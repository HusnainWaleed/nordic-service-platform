"""Build and deploy into a newly created disposable kind cluster only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.error import URLError
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from platform_cli import render


def run(*args, timeout=300):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed: {result.stdout}\n{result.stderr}')
    return result.stdout.strip()


def verify():
    suffix = uuid.uuid4().hex[:12]
    name = 'nordic-' + suffix
    image = 'nordic-service:lab-' + suffix
    # Never adopt, modify or delete a pre-existing cluster.
    if name in run('kind', 'get', 'clusters').splitlines():
        raise RuntimeError('generated cluster name already exists')
    with tempfile.TemporaryDirectory(prefix='nordic-') as temp:
        folder = Path(temp)
        kubeconfig = str(folder / 'kubeconfig')
        def kubectl(*args):
            return run('kubectl', '--kubeconfig', kubeconfig, '--context', 'kind-' + name, *args)
        attempted = False
        forward = None
        try:
            run('docker', 'build', '--tag', image, '.')
            attempted = True
            run('kind', 'create', 'cluster', '--name', name, '--kubeconfig', kubeconfig, '--wait', '120s')
            run('kind', 'load', 'docker-image', image, '--name', name)
            manifest = folder / 'service.json'
            manifest.write_text(json.dumps(render('workplace-status', image, 'synthetic-lab', local_image=True)), encoding='utf-8')
            kubectl('apply', '--dry-run=server', '-f', str(manifest))
            kubectl('apply', '-f', str(manifest))
            kubectl('rollout', 'status', 'deployment/workplace-status', '--timeout=120s')
            # kubectl selects an available local port; its log reports the binding.
            with (folder / 'forward.log').open('w+', encoding='utf-8') as log:
                forward = subprocess.Popen(['kubectl', '--kubeconfig', kubeconfig, '--context', 'kind-' + name,
                                            'port-forward', '--address=127.0.0.1', 'service/workplace-status', ':8080'],
                                           stdout=log, stderr=subprocess.STDOUT, text=True)
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    log.seek(0)
                    text = log.read()
                    import re
                    match = re.search(r'Forwarding from 127\.0\.0\.1:(\d+)', text)
                    if match:
                        try:
                            with urlopen(f'http://127.0.0.1:{match[1]}/healthz', timeout=2) as response:
                                if json.load(response) != {'status': 'ok', 'service': 'workplace-status'}:
                                    raise AssertionError('unexpected service response')
                            print('PASS: server-side validation, ready deployment and Service health endpoint')
                            return
                        except (URLError, TimeoutError, ConnectionError):
                            pass
                    if forward.poll() is not None:
                        raise RuntimeError('port-forward exited: ' + text)
                    time.sleep(.25)
                raise RuntimeError('service health check timed out')
        except Exception:
            if Path(kubeconfig).exists():
                for args in [('get', 'pods', '-o', 'wide'), ('get', 'events', '--sort-by=.metadata.creationTimestamp')]:
                    try: print(kubectl(*args))
                    except Exception as diagnostic: print(diagnostic)
            raise
        finally:
            if forward is not None:
                forward.terminate()
                try: forward.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    forward.kill(); forward.wait(timeout=10)
            if attempted:
                run('kind', 'delete', 'cluster', '--name', name, '--kubeconfig', kubeconfig)
            # Delete only the uniquely tagged image created by this run.
            run('docker', 'image', 'rm', image)


if __name__ == '__main__': verify()

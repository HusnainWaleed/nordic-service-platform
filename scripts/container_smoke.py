"""Exercise a built image with deployment-like restrictions. Requires Docker."""
import argparse
import json
import subprocess
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def docker(*args):
    return subprocess.run(['docker', *args], check=True, capture_output=True,
                          text=True, timeout=60).stdout.strip()


def verify(image):
    name = 'nordic-smoke-' + uuid.uuid4().hex[:12]
    started = False
    try:
        docker('run', '--detach', '--name', name, '--read-only', '--cap-drop=ALL',
               '--security-opt=no-new-privileges', '--user=10001:10001',
               '--memory=128m', '--cpus=0.5', '--publish=127.0.0.1::8080', image)
        started = True
        binding = json.loads(docker('inspect', '--format', '{{json .NetworkSettings.Ports}}', name))
        port = binding['8080/tcp'][0]['HostPort']
        base = f'http://127.0.0.1:{port}'
        deadline = time.monotonic() + 30
        while True:
            try:
                with urlopen(base + '/healthz', timeout=2) as response:
                    if response.status != 200 or json.load(response) != {'status': 'ok', 'service': 'workplace-status'}:
                        raise AssertionError('unexpected health response')
                break
            except (URLError, TimeoutError, ConnectionError):
                if time.monotonic() >= deadline:
                    raise RuntimeError('container did not become healthy within 30 seconds')
                time.sleep(0.25)
        try:
            with urlopen(base + '/missing', timeout=3):
                raise AssertionError('unknown route unexpectedly succeeded')
        except HTTPError as error:
            try:
                if error.code != 404:
                    raise AssertionError(f'expected 404, got {error.code}')
            finally:
                error.close()
        state = json.loads(docker('inspect', '--format', '{{json .State}}', name))
        if not state['Running'] or state.get('OOMKilled'):
            raise AssertionError('container exited or was killed for memory use')
        print('PASS: non-root container serves health JSON and returns 404 for unknown routes')
        print('PASS: read-only filesystem, all capabilities dropped, no privilege escalation, 128Mi memory limit')
    except Exception:
        if started:
            print(docker('logs', name))
        raise
    finally:
        if started:
            docker('rm', '--force', name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    verify(parser.parse_args().image)

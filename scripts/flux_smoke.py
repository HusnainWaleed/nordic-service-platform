"""Validate Git reconciliation and drift correction in a disposable cluster."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import uuid
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gitops_config import resources
from scripts.kubernetes_smoke import run
from scripts.rollback_support import failure_evidence, validate_revisions

def verify(branch, revision, rollback=False):
    scenario = json.loads(Path('gitops/rollback-scenario.json').read_text()) if rollback else None
    initial_revision = scenario['good_revision'] if rollback else revision
    if rollback:
        validate_revisions(initial_revision, scenario['bad_revision'], revision)
    config = resources(branch, initial_revision)
    if run('git', 'rev-parse', 'HEAD') != revision:
        raise ValueError('checkout must match the supplied Git revision')
    name = 'nordic-flux-' + uuid.uuid4().hex[:12]
    image = 'nordic-service:lab-000000000001'
    if name in run('kind', 'get', 'clusters').splitlines():
        raise RuntimeError('cluster already exists')
    with tempfile.TemporaryDirectory(prefix='nordic-flux-') as temp:
        folder = Path(temp); kubeconfig = str(folder/'kubeconfig')
        attempted = False
        def kube(*args):
            return run('kubectl', '--kubeconfig', kubeconfig, '--context', 'kind-'+name, *args)
        def flux(*args):
            print('Flux stage: ' + ' '.join(args), flush=True)
            return run('flux', '--kubeconfig', kubeconfig, '--context', 'kind-'+name, *args, timeout=420)
        try:
            # One fixed fixture tag is used only inside this isolated cluster.
            run('docker', 'build', '--tag', image, '.')
            attempted = True
            run('kind', 'create', 'cluster', '--name', name, '--kubeconfig', kubeconfig, '--wait', '120s')
            run('kind', 'load', 'docker-image', image, '--name', name)
            flux('install', '--version=v2.9.6', '--components=source-controller,kustomize-controller')
            kube('-n', 'flux-system', 'rollout', 'status', 'deployment/source-controller', '--timeout=180s')
            kube('-n', 'flux-system', 'rollout', 'status', 'deployment/kustomize-controller', '--timeout=180s')
            manifest = folder/'flux.json'; manifest.write_text(json.dumps(config), encoding='utf-8')
            kube('apply', '-f', str(manifest))
            flux('reconcile', 'kustomization', 'workplace', '--with-source', '--timeout=5m')
            kube('rollout', 'status', 'deployment/workplace-status', '--timeout=120s')
            applied = json.loads(kube('-n', 'flux-system', 'get', 'kustomization', 'workplace', '-o', 'json'))
            if not applied['status']['lastAppliedRevision'].endswith(initial_revision):
                raise AssertionError('Flux did not apply the requested Git revision')
            print('PASS: Flux reconciled pinned Git revision ' + initial_revision, flush=True)
            # Deliberate drift: change the replica count outside Git, then reconcile.
            kube('scale', 'deployment/workplace-status', '--replicas=2')
            current = json.loads(kube('get', 'deployment/workplace-status', '-o', 'json'))
            if current['spec']['replicas'] != 2:
                raise AssertionError('drift injection was not observed')
            flux('reconcile', 'kustomization', 'workplace', '--timeout=3m')
            current = json.loads(kube('get', 'deployment/workplace-status', '-o', 'json'))
            if current['spec']['replicas'] != 1:
                raise AssertionError('Flux did not restore the Git replica count')
            kube('rollout', 'status', 'deployment/workplace-status', '--timeout=120s')
            print('PASS: injected replica drift was corrected from 2 to 1')
            if rollback:
                def health():
                    result = kube('exec', 'deployment/workplace-status', '--', 'python', '-c',
                                  "import urllib.request; print(urllib.request.urlopen('http://workplace-status:8080/healthz', timeout=5).read().decode())")
                    if json.loads(result) != {'status': 'ok', 'service': 'workplace-status'}:
                        raise AssertionError('unexpected Service health response')
                def promote(commit):
                    kube('-n', 'flux-system', 'patch', 'gitrepository', 'workplace', '--type=merge',
                         '-p', json.dumps({'spec': {'ref': {'branch': branch, 'commit': commit}}}))
                health()
                # Limit the expected failure observation to a bounded health check.
                kube('-n', 'flux-system', 'patch', 'kustomization', 'workplace', '--type=merge',
                     '-p', json.dumps({'spec': {'timeout': '30s'}}))
                promote(scenario['bad_revision'])
                try:
                    flux('reconcile', 'kustomization', 'workplace', '--with-source', '--timeout=90s')
                except RuntimeError:
                    pass  # Accepted only after checking precise controller evidence below.
                else:
                    raise AssertionError('bad revision unexpectedly reconciled successfully')
                failed = json.loads(kube('-n', 'flux-system', 'get', 'kustomization', 'workplace', '-o', 'json'))
                deployment = json.loads(kube('get', 'deployment/workplace-status', '-o', 'json'))
                evidence = failure_evidence(failed, deployment, scenario['bad_revision'])
                print('PASS: observed HealthCheckFailed for deliberately broken Git revision', flush=True)
                start = time.monotonic()
                promote(revision)
                flux('reconcile', 'kustomization', 'workplace', '--with-source', '--timeout=3m')
                kube('rollout', 'status', 'deployment/workplace-status', '--timeout=120s')
                recovered = json.loads(kube('-n', 'flux-system', 'get', 'kustomization', 'workplace', '-o', 'json'))
                if not recovered['status']['lastAppliedRevision'].endswith(revision):
                    raise AssertionError('recovery commit was not applied')
                deployment = json.loads(kube('get', 'deployment/workplace-status', '-o', 'json'))
                if deployment['spec']['template']['spec']['containers'][0]['readinessProbe']['httpGet']['path'] != '/healthz':
                    raise AssertionError('recovery did not restore the readiness probe')
                health()
                evidence.update({'good_revision': initial_revision, 'recovery_revision': revision,
                                 'recovery_seconds': round(time.monotonic()-start, 3),
                                 'service_health_before_and_after': 'verified',
                                 'measurement_scope': 'promotion request through rollout and Service verification in disposable hosted CI'})
                Path('work').mkdir(exist_ok=True)
                Path('work/rollback-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
                print('PASS: recovery Git commit restored readiness and Service health', flush=True)
                print(json.dumps(evidence, indent=2), flush=True)
        except Exception:
            if Path(kubeconfig).exists():
                for args in [('get', 'pods', '-A'), ('get', 'events', '-A', '--sort-by=.metadata.creationTimestamp'),
                             ('-n', 'flux-system', 'get', 'gitrepositories,kustomizations', '-o', 'yaml')]:
                    try: print(kube(*args))
                    except Exception as error: print(error)
            raise
        finally:
            if attempted:
                run('kind', 'delete', 'cluster', '--name', name, '--kubeconfig', kubeconfig)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', required=True); parser.add_argument('--revision', required=True)
    parser.add_argument('--rollback', action='store_true', help='Promote good, deliberately bad and recovery Git revisions')
    args = parser.parse_args(); verify(args.branch, args.revision, rollback=args.rollback)

"""Validate Git reconciliation and drift correction in a disposable cluster."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gitops_config import resources
from scripts.kubernetes_smoke import run

def verify(branch, revision):
    config = resources(branch, revision)
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
            if not applied['status']['lastAppliedRevision'].endswith(revision):
                raise AssertionError('Flux did not apply the requested Git revision')
            print('PASS: Flux reconciled pinned Git revision ' + revision)
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
        except Exception:
            if Path(kubeconfig).exists():
                for args in [('get', 'pods', '-A'), ('get', 'events', '-A', '--sort-by=.metadata.creationTimestamp')]:
                    try: print(kube(*args))
                    except Exception as error: print(error)
            raise
        finally:
            if attempted:
                run('kind', 'delete', 'cluster', '--name', name, '--kubeconfig', kubeconfig)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', required=True); parser.add_argument('--revision', required=True)
    args = parser.parse_args(); verify(args.branch, args.revision)

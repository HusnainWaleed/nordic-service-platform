"""Generate an inspectable deployment bundle; never apply it automatically."""
import argparse
import json
import re
from pathlib import Path

def render(name, image, owner):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,38}[a-z0-9]|[a-z]', name):
        raise ValueError('service name must be a DNS label of 1-40 characters')
    if not re.fullmatch(r'[a-z0-9][a-z0-9._/-]*(?::[a-z0-9._-]+)?@sha256:[0-9a-f]{64}', image):
        raise ValueError('image must use an immutable sha256 digest')
    if not owner.strip() or len(owner) > 80:
        raise ValueError('owner must contain 1-80 characters')
    labels = {'app.kubernetes.io/name': name}
    return {'apiVersion': 'v1', 'kind': 'List', 'items': [
        {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'name': name, 'annotations': {'portfolio/owner': owner}},
         'spec': {'replicas': 1, 'selector': {'matchLabels': labels}, 'template': {'metadata': {'labels': labels}, 'spec': {
             'automountServiceAccountToken': False,
             'securityContext': {'runAsNonRoot': True, 'runAsUser': 10001, 'seccompProfile': {'type': 'RuntimeDefault'}},
             'containers': [{'name': name, 'image': image, 'ports': [{'containerPort': 8080}],
                 'resources': {'requests': {'cpu': '100m', 'memory': '64Mi'}, 'limits': {'cpu': '500m', 'memory': '128Mi'}},
                 'securityContext': {'allowPrivilegeEscalation': False, 'readOnlyRootFilesystem': True, 'capabilities': {'drop': ['ALL']}},
                 'readinessProbe': {'httpGet': {'path': '/healthz', 'port': 8080}, 'initialDelaySeconds': 2},
                 'livenessProbe': {'httpGet': {'path': '/healthz', 'port': 8080}, 'initialDelaySeconds': 5}}]}}}},
        {'apiVersion': 'v1', 'kind': 'Service', 'metadata': {'name': name}, 'spec': {'selector': labels, 'ports': [{'port': 8080, 'targetPort': 8080}]}}
    ]}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('name'); p.add_argument('--image', required=True); p.add_argument('--owner', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    try:
        bundle = render(args.name, args.image, args.owner)
        with args.output.open('x', encoding='utf-8') as f:
            json.dump(bundle, f, indent=2)
    except (ValueError, OSError) as e:
        p.exit(2, str(e) + '\n')

if __name__ == '__main__': main()

"""Validate controller and deployment evidence for an intentional bad release."""
import re

def validate_revisions(good, bad, recovery):
    if any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}', value)
           for value in [good, bad, recovery]) or len({good, bad, recovery}) != 3:
        raise ValueError('good, bad and recovery must be distinct full Git commit SHAs')

def failure_evidence(kustomization, deployment, revision):
    status = kustomization.get('status', {})
    conditions = status.get('conditions', [])
    failed = next((c for c in conditions if c.get('type') == 'Ready'), {})
    if failed.get('status') != 'False' or failed.get('reason') != 'HealthCheckFailed':
        raise AssertionError('expected a Flux health check failure, not a transport or source error')
    if not status.get('lastAttemptedRevision', '').endswith(revision):
        raise AssertionError('Flux did not attempt the expected bad Git revision')
    if status.get('observedGeneration', -1) < kustomization['metadata']['generation']:
        raise AssertionError('Flux failure is stale')
    if deployment.get('status', {}).get('observedGeneration', -1) < deployment['metadata']['generation']:
        raise AssertionError('Deployment controller has not observed the bad rollout')
    path = deployment['spec']['template']['spec']['containers'][0]['readinessProbe']['httpGet']['path']
    if path != '/not-ready':
        raise AssertionError('expected deliberately broken readiness probe')
    return {'bad_revision': revision, 'condition': failed['reason'], 'readiness_path': path}

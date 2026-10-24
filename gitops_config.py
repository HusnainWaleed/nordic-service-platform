"""Create Flux resources for the public portfolio repository."""
import re

def resources(branch, revision):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('a full 40-character Git commit SHA is required')
    if not branch or len(branch) > 200 or not re.fullmatch(r'[A-Za-z0-9_./-]+', branch):
        raise ValueError('invalid branch')
    return {'apiVersion': 'v1', 'kind': 'List', 'items': [
        {'apiVersion': 'source.toolkit.fluxcd.io/v1', 'kind': 'GitRepository',
         'metadata': {'name': 'workplace', 'namespace': 'flux-system'},
         'spec': {'interval': '30s', 'url': 'https://github.com/HusnainWaleed/nordic-service-platform',
                  'ref': {'branch': branch, 'commit': revision}}},
        {'apiVersion': 'kustomize.toolkit.fluxcd.io/v1', 'kind': 'Kustomization',
         'metadata': {'name': 'workplace', 'namespace': 'flux-system'},
         'spec': {'interval': '30s', 'path': './gitops/app', 'targetNamespace': 'default', 'prune': True, 'wait': True,
                  'timeout': '120s', 'sourceRef': {'kind': 'GitRepository', 'name': 'workplace'}}}
    ]}

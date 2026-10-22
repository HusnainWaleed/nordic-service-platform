import unittest
from platform_cli import render

IMAGE = 'ghcr.io/example/workplace-status@sha256:' + 'a' * 64
class PlatformTests(unittest.TestCase):
    def test_deployment_contract(self):
        bundle = render('workplace-status', IMAGE, 'lab-team')
        deployment, service = bundle['items']
        spec = deployment['spec']['template']['spec']
        self.assertFalse(spec['automountServiceAccountToken'])
        self.assertEqual(service['spec']['selector'], deployment['spec']['selector']['matchLabels'])
        self.assertTrue(spec['containers'][0]['securityContext']['readOnlyRootFilesystem'])
    def test_rejects_mutable_image(self):
        with self.assertRaises(ValueError): render('status', 'python:latest', 'lab')
    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError): render('../escape', IMAGE, 'lab')
    def test_rejects_missing_owner(self):
        with self.assertRaises(ValueError): render('status', IMAGE, ' ')

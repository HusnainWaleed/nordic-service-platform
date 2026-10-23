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
    def test_local_tag_requires_opt_in(self):
        with self.assertRaises(ValueError):
            render('status', 'nordic-service:lab-123456abcdef', 'lab')
    def test_local_image_never_pulls(self):
        result = render('status', 'nordic-service:lab-123456abcdef', 'lab', local_image=True)
        container = result['items'][0]['spec']['template']['spec']['containers'][0]
        self.assertEqual(container['imagePullPolicy'], 'Never')
    def test_local_mode_rejects_latest_and_arbitrary_images(self):
        for image in ['nordic-service:latest', 'other:lab-123456abcdef', IMAGE]:
            with self.subTest(image=image), self.assertRaises(ValueError):
                render('status', image, 'lab', local_image=True)

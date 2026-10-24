import unittest
from gitops_config import resources

class GitOpsConfigTests(unittest.TestCase):
    def test_source_is_pinned_and_points_to_public_repo(self):
        source, apply = resources('main', 'a' * 40)['items']
        self.assertEqual(source['spec']['ref'], {'branch': 'main', 'commit': 'a' * 40})
        self.assertEqual(source['spec']['url'], 'https://github.com/HusnainWaleed/nordic-service-platform')
        self.assertNotIn('secretRef', source['spec'])
        self.assertEqual(apply['spec']['sourceRef']['name'], source['metadata']['name'])
    def test_wait_and_prune_are_explicit(self):
        apply = resources('main', 'b' * 40)['items'][1]
        self.assertTrue(apply['spec']['wait'])
        self.assertTrue(apply['spec']['prune'])
        self.assertEqual(apply['spec']['path'], './gitops/app')
    def test_mutable_or_invalid_revisions_are_rejected(self):
        for revision in ['main', '', 'a'*39, 'z'*40]:
            with self.subTest(revision=revision), self.assertRaises(ValueError): resources('main', revision)
    def test_invalid_branch_is_rejected(self):
        for branch in ['', 'main; echo bad', 'main\nother']:
            with self.subTest(branch=branch), self.assertRaises(ValueError): resources(branch, 'a'*40)

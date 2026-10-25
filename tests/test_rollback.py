import copy
import unittest
from scripts.rollback_support import failure_evidence, validate_revisions

class RollbackEvidenceTests(unittest.TestCase):
    def snapshots(self):
        # Synthetic controller snapshots validate evidence handling, not cluster behavior.
        return ({'metadata': {'generation': 2}, 'status': {'observedGeneration': 2,
                 'lastAttemptedRevision': 'branch@sha1:' + 'b'*40,
                 'conditions': [{'type': 'Ready', 'status': 'False', 'reason': 'HealthCheckFailed'}]}},
                {'metadata': {'generation': 3}, 'status': {'observedGeneration': 3},
                 'spec': {'template': {'spec': {'containers': [{'readinessProbe': {'httpGet': {'path': '/not-ready'}}}]}}}})
    def test_accepts_expected_failure(self):
        k, d = self.snapshots()
        self.assertEqual(failure_evidence(k, d, 'b'*40)['condition'], 'HealthCheckFailed')
    def test_transport_failure_does_not_count_as_failed_release(self):
        k, d = self.snapshots(); k['status']['conditions'][0]['reason'] = 'ArtifactFailed'
        with self.assertRaises(AssertionError): failure_evidence(k, d, 'b'*40)
    def test_wrong_revision_is_rejected(self):
        k, d = self.snapshots()
        with self.assertRaises(AssertionError): failure_evidence(k, d, 'c'*40)
    def test_stale_controller_status_is_rejected(self):
        for index in [0, 1]:
            snapshots = self.snapshots(); snapshots[index]['status']['observedGeneration'] = 0
            with self.subTest(index=index), self.assertRaises(AssertionError):
                failure_evidence(*snapshots, 'b'*40)
    def test_healthy_probe_cannot_count_as_injected_failure(self):
        k, d = self.snapshots(); d['spec']['template']['spec']['containers'][0]['readinessProbe']['httpGet']['path'] = '/healthz'
        with self.assertRaises(AssertionError): failure_evidence(k, d, 'b'*40)
    def test_revisions_must_be_distinct_and_immutable(self):
        validate_revisions('a'*40, 'b'*40, 'c'*40)
        for args in [('main', 'b'*40, 'c'*40), ('a'*40, 'a'*40, 'c'*40)]:
            with self.assertRaises(ValueError): validate_revisions(*args)

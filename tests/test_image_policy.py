import copy
import unittest
from scripts.image_policy import evaluate


class ImagePolicyTests(unittest.TestCase):
    def report(self, severity='HIGH', fixed='2.0'):
        # Synthetic policy fixtures, not evidence from a real image scan.
        return {'SchemaVersion': 2, 'Metadata': {'OS': {'Family': 'debian', 'EOSL': False}},
                'Results': [{'Target': 'synthetic', 'Class': 'os-pkgs', 'Vulnerabilities': [
                    {'VulnerabilityID': 'SYNTHETIC-1', 'PkgName': 'example',
                     'InstalledVersion': '1.0', 'FixedVersion': fixed, 'Severity': severity}]}]}

    def test_fixable_high_and_critical_block(self):
        for severity in ['HIGH', 'CRITICAL']:
            with self.subTest(severity=severity):
                self.assertEqual(len(evaluate(self.report(severity))['blocking']), 1)

    def test_unfixed_high_remains_visible_without_blocking(self):
        summary = evaluate(self.report(fixed=''))
        self.assertEqual(summary, {'counts': {'HIGH': 1}, 'blocking': []})

    def test_medium_is_reported_without_blocking(self):
        self.assertEqual(evaluate(self.report('MEDIUM'))['counts'], {'MEDIUM': 1})
        self.assertFalse(evaluate(self.report('MEDIUM'))['blocking'])

    def test_empty_vulnerability_result_is_valid(self):
        report = self.report()
        report['Results'][0]['Vulnerabilities'] = None
        self.assertFalse(evaluate(report)['blocking'])

    def test_missing_scan_data_is_rejected(self):
        for bad in [{}, [], {'SchemaVersion': 2, 'Results': []},
                    {'SchemaVersion': 2, 'Results': [{}]}]:
            with self.subTest(report=bad), self.assertRaises(ValueError): evaluate(bad)

    def test_eol_operating_system_is_rejected(self):
        report = self.report(); report['Metadata']['OS']['EOSL'] = True
        with self.assertRaises(ValueError): evaluate(report)

    def test_malformed_findings_are_rejected(self):
        for finding in [None, {}, {'Severity': 'TYPO'}, {'Severity': 'HIGH', 'FixedVersion': 3}]:
            report = self.report(); report['Results'][0]['Vulnerabilities'] = [finding]
            with self.subTest(finding=finding), self.assertRaises(ValueError): evaluate(report)

    def test_report_is_not_modified(self):
        report = self.report(); original = copy.deepcopy(report)
        evaluate(report)
        self.assertEqual(report, original)
    def test_empty_objects_and_strings_are_not_clean_lists(self):
        for invalid in [{}, '', 0]:
            report = self.report(); report['Results'][0]['Vulnerabilities'] = invalid
            with self.subTest(value=invalid), self.assertRaises(ValueError): evaluate(report)
    def test_missing_package_scan_is_rejected(self):
        report = self.report(); report['Results'][0].pop('Class')
        with self.assertRaises(ValueError): evaluate(report)

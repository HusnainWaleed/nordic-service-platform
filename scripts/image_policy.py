"""Evaluate a full Trivy JSON report without suppressing unfixed findings."""
import argparse
import json
from pathlib import Path


def evaluate(report):
    if not isinstance(report, dict) or report.get('SchemaVersion') != 2:
        raise ValueError('expected a Trivy schema version 2 report')
    results = report.get('Results')
    if not isinstance(results, list) or not results:
        raise ValueError('report must contain scan results')
    if not isinstance(report.get('Metadata'), dict) or not isinstance(report['Metadata'].get('OS'), dict):
        raise ValueError('operating system metadata is required for this image')
    if report['Metadata']['OS'].get('EOSL'):
        raise ValueError('image operating system is end of life')
    if not any(isinstance(result, dict) and result.get('Class') == 'os-pkgs' for result in results):
        raise ValueError('operating system package scan result is required')
    counts = {}
    blocking = []
    for result in results:
        if not isinstance(result, dict):
            raise ValueError('invalid result object')
        vulnerabilities = result.get('Vulnerabilities')
        if vulnerabilities is None:
            vulnerabilities = []
        if not isinstance(vulnerabilities, list):
            raise ValueError('invalid vulnerability list')
        for finding in vulnerabilities:
            if not isinstance(finding, dict) or not isinstance(finding.get('Severity'), str):
                raise ValueError('vulnerability severity is required')
            severity = finding['Severity']
            if severity not in {'UNKNOWN', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}:
                raise ValueError('unrecognized severity')
            counts[severity] = counts.get(severity, 0) + 1
            fixed = finding.get('FixedVersion', '')
            if not isinstance(fixed, str):
                raise ValueError('invalid fixed version')
            if severity in {'HIGH', 'CRITICAL'} and fixed.strip():
                blocking.append({
                    'target': result.get('Target', ''),
                    'id': finding.get('VulnerabilityID', ''),
                    'package': finding.get('PkgName', ''),
                    'installed': finding.get('InstalledVersion', ''),
                    'fixed': fixed,
                    'severity': severity,
                })
    return {'counts': counts, 'blocking': blocking}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    try:
        summary = evaluate(json.loads(args.report.read_text(encoding='utf-8')))
    except (ValueError, OSError) as error:
        parser.exit(2, f'Scan report rejected: {error}\n')
    print(json.dumps(summary, indent=2))
    if summary['blocking']:
        parser.exit(1, 'Image gate failed: fixable HIGH or CRITICAL vulnerabilities found.\n')
    print('PASS: no fixable HIGH or CRITICAL vulnerabilities reported; review the full report for remaining risk.')


if __name__ == '__main__': main()

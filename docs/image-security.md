# Container vulnerability checks

## Policy
The `image-security` CI job builds the sample image and scans OS and supported language packages with Trivy v0.76.1. It saves the full JSON report before enforcing a separate, tested policy. HIGH and CRITICAL findings block the job when `FixedVersion` is non-empty. Other findings remain visible and require review. Unsupported or missing scan data and end-of-life operating systems fail the policy rather than count as a clean scan.

No ignore list, blanket exception or `continue-on-error` is used. The initial threshold is a lab policy, not an assertion that unfixed or lower-severity findings are safe. A clean gate is not proof that an image is secure. Exploitability, exposure and compensating controls need separate assessment.

## Evidence
Each run uploads `image-security-report` for 14 days, including the unfiltered report, scanner version and local image ID. The report contains scan timestamps and image metadata. Downloads and vulnerability database failures fail the job; artifact upload is attempted even when scanning or policy evaluation fails. No registry image is published.

The scanner version is pinned and its official release checksum is checked before execution. Vulnerability databases are refreshed by Trivy and change over time, so results may change without a source change. Local image IDs are not registry manifest digests and must not be substituted into the deployment generator's digest reference.

## Run locally
With Docker running and Trivy v0.76.1 installed from its official release:

```sh
docker build --pull --tag nordic-service:scan .
mkdir -p work
trivy image --image-src docker --scanners vuln --format json --output work/trivy-image.json --exit-code 0 nordic-service:scan
python scripts/image_policy.py work/trivy-image.json
```

On PowerShell, create the directory with `New-Item -ItemType Directory -Force work`. Policy exit codes are 0 for threshold pass, 1 for blocking findings, and 2 for an unreadable or invalid report.

## Respond to a failed gate
Review the full report, affected package, installed version and fixed version. Update the relevant base image or application dependency, rebuild, rerun container/Kubernetes checks and rescan. If upstream has no applicable fix, document the investigation; do not suppress a finding just to obtain a green badge. This milestone does not add automated remediation, image signing, SBOM generation or secret scanning.

References: https://trivy.dev/docs/latest/configuration/filtering/ and https://github.com/aquasecurity/trivy/releases/tag/v0.76.1

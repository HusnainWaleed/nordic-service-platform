# Container validation

## User problem
The initial deployment bundle specified non-root execution and a read-only filesystem, but nothing verified whether the sample image could run under those restrictions. Python tests alone cannot detect container startup failures.

## Reproduce
With Docker running, execute these commands from the repository root:

```sh
python -m unittest discover -s tests -v
docker build --pull --tag nordic-service:local .
python scripts/container_smoke.py --image nordic-service:local
```

The smoke check binds an ephemeral port on loopback, runs as UID/GID 10001 with a read-only filesystem, drops Linux capabilities, disables privilege escalation and limits memory to 128Mi. It checks the exact health JSON, verifies that an unknown route returns 404 and confirms the container remains running. It removes only its uniquely named test container, including on failure. Docker image build and smoke checks also run on pull requests without registry credentials or image publication.

## Scope and limitations
This verifies the sample container, not Kubernetes networking, scheduling, admission or health-probe behavior. CI uses Linux containers; a local Docker daemon must support Linux containers. The base image tag receives upstream changes, so this is a repeatable validation procedure rather than a bit-for-bit reproducible image build. Pinning and renewing the base image digest is a later supply-chain improvement.

## Evidence
The workstation Docker engine was unavailable when this milestone was prepared. Local HTTP contract tests verify health JSON and 404 handling; the pull request's container job supplies the actual image-build and runtime evidence. Do not claim a container test passed unless that job or the local smoke command has completed successfully.

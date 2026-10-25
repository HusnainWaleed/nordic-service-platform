# Git revision rollback drill

## Scenario
This is a synthetic release experiment in a disposable kind cluster, not a production incident. `gitops/rollback-scenario.json` records a known-good revision and a deliberately bad lab revision. The bad commit changes the sample Deployment readiness path to `/not-ready`. Its child restores `/healthz` and adds this drill; the active branch contains the healthy manifest. The bad snapshot is retained as reproducible test input, not merged as the active desired state.

CI promotes exact Git revisions by updating the bootstrap GitRepository commit pin. Flux fetches and applies each desired manifest from Git. No application Deployment is manually patched during rollback. This verifies deliberate revision promotion and recovery, not automatic release selection or an autonomous rollback policy. The CI token stays read-only and the drill does not push commits or modify remote branches.

## Acceptance criteria
1. The known-good revision reconciles and the Service returns the exact health JSON.
2. The existing drift test restores replicas from two to one.
3. The bad revision is attempted, the Deployment controller observes the changed template, and Flux reports `Ready=False` with `HealthCheckFailed` for that revision. A Git fetch error, timeout alone, stale status or wrong revision does not count as an observed failed release.
4. The recovery commit reconciles, restores `/healthz`, completes rollout and serves the expected health JSON through the Kubernetes Service.
5. The script saves the exact revisions and measured recovery interval to `work/rollback-evidence.json`. CI retains this artifact for 14 days.

The recovery interval starts immediately before requesting promotion of the recovery commit and ends after rollout and Service verification. It excludes diagnosis, human review and bad-release detection. It is one hosted lab measurement, not a production recovery objective or downtime measurement. Rolling updates may keep an old healthy pod serving while the bad revision is unready; this experiment does not claim an outage occurred.

## Reproduce
Use a checkout and public branch containing the final recovery commit, with Docker, kind v0.33.0, kubectl and Flux v2.9.6 available:

```sh
python scripts/flux_smoke.py --branch YOUR_BRANCH --revision YOUR_FULL_COMMIT_SHA --rollback
```

Keep the scenario commits reachable in repository history; use merge commits rather than squashing away the deliberate bad snapshot when integrating this experiment. The script creates and deletes only its own cluster, uses a temporary kubeconfig and retains the shared local fixture image. No existing cluster context, production namespace or paid resource is used.

## Remaining work
Controller metrics, application observability, additional failure scenarios, production RBAC and a narrated demonstration remain future milestones. The 44 unfixed HIGH findings previously recorded by image scanning are separate residual risk; a successful recovery drill does not resolve those findings.

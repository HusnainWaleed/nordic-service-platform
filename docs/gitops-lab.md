# Git reconciliation and drift recovery

## Purpose
Direct Kubernetes apply checks validate deployment behavior. They do not show a controller reading desired state from Git. This lab installs Flux source-controller and kustomize-controller into a new kind cluster, pins the public source to an exact branch and commit, and waits for Flux to apply `gitops/app`.

The committed manifests are synthetic fixtures for this disposable lab. Their fixed preloaded image tag uses `imagePullPolicy: Never`; it is not a registry release or a production deployment. The test builds that image from the checked-out code and loads it into its own node. No Git credentials, write access, registry publication or paid cloud infrastructure are required.

## Validation
After confirming the applied Git revision and deployment readiness, the script injects replica drift from one to two outside Git, verifies the mutation and requests reconciliation. It then asserts that Flux restores one replica and the rollout remains ready. This tests initial reconciliation and drift recovery. It does not yet demonstrate a bad Git release followed by a revert commit.

## Reproduce
Install Docker with Linux containers, kind v0.33.0, kubectl and Flux CLI v2.9.6. Use a branch and full commit SHA that already contain this lab in the public GitHub repository. Run from the repository root:

```sh
python scripts/flux_smoke.py --branch YOUR_BRANCH --revision YOUR_FULL_COMMIT_SHA
```

The checkout must match the supplied revision. CI passes the pull request head revision and branch. The script creates a temporary kubeconfig, names its cluster uniquely and deletes its cluster afterward. The local fixture image is deliberately retained to avoid deleting a shared tag that another lab run may use. A hard interruption can leave a cluster behind; inspect names before any manual cleanup.

## Rollback runbook and remaining experiment
For a future Git-managed release failure, revert the responsible Git change through review, reconcile the source, wait for the Kustomization's Ready condition and verify the application and applied revision. Do not treat `kubectl rollout undo` as a durable rollback while Flux is reconciling the unchanged Git desired state; the controller can overwrite that manual change.

The optional [rollback drill](rollback-drill.md) adds a bad Git revision, a recovery commit and Service HTTP verification before and after recovery. Controller observability and a restricted service-account design remain future work. Controller installation here uses cluster-admin permissions inside an ephemeral cluster only. No production readiness or local workstation execution is claimed. Actual execution evidence comes from a successful `gitops` CI job.

References: https://fluxcd.io/flux/faq/ and https://fluxcd.io/flux/components/kustomize/kustomizations/

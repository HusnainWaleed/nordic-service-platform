# Disposable Kubernetes deployment validation

The container check does not establish that a generated Deployment can be admitted, scheduled or reached through a Kubernetes Service. This experiment builds the sample image, creates a uniquely named kind cluster with a temporary kubeconfig, loads the image, validates the generated bundle against the API server, waits for rollout readiness and verifies exact health JSON through Service port forwarding.

## Reproduce
Install Docker with Linux containers, kubectl and kind v0.33.0 using official installation instructions. Start Docker and run from the repository root:

```sh
python -m unittest discover -s tests -v
python scripts/kubernetes_smoke.py
```

The script always creates its own cluster. It does not use your current Kubernetes context or shared kubeconfig. Cleanup stops its port forward and deletes only its uniquely named cluster and image. A hard process termination or machine shutdown can interrupt cleanup; inspect `kind get clusters` and the run output before removing leftovers.

## Local image exception
Registry deployments remain digest-only by default. The explicit `--local-image` option accepts only `nordic-service:lab-` plus 12 hex characters and sets `imagePullPolicy: Never`. This allows kind to use an image loaded into the node, without publishing a registry image or silently weakening the default contract. A missing local image should fail deployment rather than pull anything.

## Evidence and limits
The workstation Docker daemon remains unavailable. Actual Kubernetes execution is performed by the pull request's `kubernetes` CI job; only a successful job is deployment evidence. The test covers one disposable Linux node, not production availability, cloud networking, ingress, GitOps or multi-tenancy. kind is version-pinned; the Python base image and kind's default node image are not fully digest-pinned, so bit-for-bit reproducibility is not claimed.

Reference: https://kind.sigs.k8s.io/docs/user/quick-start/

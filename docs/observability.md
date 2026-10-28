# Application request observability

## Signals
The sample app exposes `/metrics` in Prometheus text format 0.0.4 and writes one JSON request summary per handled GET to stderr. Request count and duration sum/count use only bounded route labels (`/`, `/healthz`, `unmatched`) and status labels (200, 404). Unknown raw paths, query strings, client addresses and headers are not included. Scrapes are excluded from application request metrics, but have structured log summaries.

The standard-library exporter is intentionally small: a lock protects concurrent updates and each process maintains its own counters. Counts reset on restart; there is no persistence, cross-replica aggregation, histogram, latency percentile or tracing. Duration measures the server handler through the response write attempt, not end-to-end client latency or guaranteed successful delivery. Unsupported HTTP methods are not instrumented. This is a lab service, not a hardened production HTTP server.

## Run locally
Start `python app.py`, request `/healthz` and a missing path, then inspect `http://localhost:8080/metrics`. To verify with real Prometheus, start Docker with Linux containers and run:

```sh
docker build --pull --tag nordic-service:metrics .
python scripts/observability_smoke.py --image nordic-service:metrics
```

The integration creates uniquely named application and Prometheus containers on a temporary Docker network. Host ports bind only to loopback. Prometheus v3.15.1 scrapes once per second and its HTTP query API must return the expected health request, 404 and duration-count series. Cleanup removes only the containers, anonymous volumes and network created by this run. A hard interruption may require inspecting and removing leftovers manually. No Docker socket is mounted in either container.

## Evidence and investigation
CI uploads `observability-evidence` for 14 days, including the scrape/query results, timestamp, application image ID and Prometheus image ID. These IDs identify the tested local Docker images; they are not registry manifest digests. The test also verifies that a synthetic query value is absent from logs and metrics. The Prometheus image uses a version tag, not an immutable digest.

Useful initial queries are `up{job="workplace"}`, `workplace_http_requests_total`, and `rate(workplace_http_request_duration_seconds_sum[5m]) / rate(workplace_http_request_duration_seconds_count[5m])`. The last expression is a mean duration, not a percentile. Check scrape health before interpreting application series; zero samples can mean missing telemetry rather than zero requests. Readiness health is separate from business success.

This milestone validates Docker-based application scraping only. No Kubernetes Prometheus deployment, Grafana dashboard, alert delivery, SLO attainment or controller-metrics coverage is claimed. Metrics have no authentication and must not be exposed publicly without an access-control design. The existing recovery drill and image vulnerability findings remain separate evidence and risks.

References: https://prometheus.io/docs/instrumenting/exposition_formats/ and https://prometheus.io/docs/practices/naming/

"""Prove that a real Prometheus instance can scrape and query the sample app."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

PROMETHEUS = 'prom/prometheus:v3.15.1'

def docker(*args):
    return subprocess.run(['docker', *args], check=True, capture_output=True,
                          text=True, timeout=180).stdout.strip()

def binding(name, port):
    ports = json.loads(docker('inspect', '--format', '{{json .NetworkSettings.Ports}}', name))
    return 'http://127.0.0.1:' + ports[f'{port}/tcp'][0]['HostPort']

def read_json(url):
    with urlopen(url, timeout=3) as response: return json.load(response)

def verify(image):
    suffix = uuid.uuid4().hex[:12]
    network, app, prom = ['nordic-'+part+'-'+suffix for part in ['metrics-net', 'app', 'prom']]
    created = []
    network_created = False
    Path('work').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='metrics-', dir='work') as temp:
        try:
            docker('network', 'create', network); network_created = True
            docker('run', '--detach', '--name', app, '--network', network,
                   '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                   '--user=10001:10001', '--memory=128m', '--publish=127.0.0.1::8080', image)
            created.append(app)
            base = binding(app, 8080)
            deadline = time.monotonic()+30
            while True:
                try:
                    if read_json(base+'/healthz') != {'status':'ok','service':'workplace-status'}:
                        raise AssertionError('unexpected health JSON')
                    break
                except (URLError, TimeoutError, ConnectionError):
                    if time.monotonic() >= deadline: raise
                    time.sleep(.25)
            try:
                with urlopen(base+'/missing?token=synthetic-only', timeout=3):
                    raise AssertionError('expected unknown route to fail')
            except HTTPError as error:
                try:
                    if error.code != 404: raise AssertionError('expected HTTP 404')
                finally: error.close()
            config = Path(temp).resolve()/'prometheus.json'
            config.write_text(json.dumps({'global': {'scrape_interval':'1s'},
                'scrape_configs':[{'job_name':'workplace','static_configs':[{'targets':[app+':8080']}]}]}), encoding='utf-8')
            docker('run', '--detach', '--name', prom, '--network', network,
                   '--cap-drop=ALL', '--security-opt=no-new-privileges', '--memory=256m',
                   '--publish=127.0.0.1::9090', '--mount',
                   f'type=bind,src={config},dst=/etc/prometheus/prometheus.yml,readonly', PROMETHEUS)
            created.append(prom)
            prom_base = binding(prom, 9090)
            expressions = {
                'scrape_up':'up{job="workplace"}',
                'health_requests':'workplace_http_requests_total{route="/healthz",status="200"}',
                'not_found_requests':'workplace_http_requests_total{route="unmatched",status="404"}',
                'duration_observations':'workplace_http_request_duration_seconds_count{route="/healthz",status="200"}',
            }
            results = {}; deadline = time.monotonic()+90
            while time.monotonic() < deadline:
                try:
                    for label, query in expressions.items():
                        response = read_json(prom_base+'/api/v1/query?'+urlencode({'query':query}))
                        if response.get('status') != 'success': raise AssertionError('Prometheus query failed')
                        results[label] = response['data']['result']
                    if all(rows and float(rows[0]['value'][1]) >= 1 for rows in results.values()): break
                except (URLError, TimeoutError, ConnectionError): pass
                time.sleep(.5)
            else: raise AssertionError('Prometheus did not ingest the expected request and duration series')
            # Confirm synthetic query values are absent from the app logs and exposed metrics.
            with urlopen(base+'/metrics', timeout=3) as response: metrics = response.read().decode()
            # Docker puts app stderr in the subprocess stderr stream.
            all_logs = subprocess.run(['docker','logs',app], check=True, capture_output=True, text=True, timeout=30)
            if 'synthetic-only' in metrics+all_logs.stdout+all_logs.stderr:
                raise AssertionError('query value leaked into telemetry')
            evidence = {'timestamp_utc':datetime.now(timezone.utc).isoformat(),
                        'application_image_id':docker('inspect','--format','{{.Image}}',app),
                        'prometheus_image':PROMETHEUS,
                        'prometheus_image_id':docker('inspect','--format','{{.Image}}',prom),
                        'queries':expressions,'results':results,
                        'scope':'synthetic traffic in isolated Docker containers; not production availability'}
            Path('work/observability-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
            print('PASS: Prometheus scraped the app and queried health, 404 and duration series')
            print('PASS: synthetic query value is absent from metrics and request logs')
        except Exception:
            for name in created:
                result = subprocess.run(['docker','logs',name],capture_output=True,text=True,timeout=30)
                print(result.stdout+result.stderr)
            raise
        finally:
            for name in reversed(created): docker('rm','--force','--volumes',name)
            if network_created: docker('network','rm',network)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--image',required=True)
    verify(parser.parse_args().image)

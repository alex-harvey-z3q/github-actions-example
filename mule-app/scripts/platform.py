"""Credential-free Exchange/CloudHub stand-ins. Never calls Anypoint or Azure/AWS."""
import argparse
import contextlib
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

GROUP = 'org.example.mule'
ARTIFACT = 'synthetic-timetable-api'
NS = {'m': 'http://maven.apache.org/POM/4.0.0'}


def validate_version(version):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Use an explicit release version, such as 1.0.0')
    return version


def set_version(version):
    validate_version(version)
    ET.register_namespace('', NS['m'])
    root = ET.parse('pom.xml')
    root.find('m:version', NS).text = version
    root.write('pom.xml', encoding='UTF-8', xml_declaration=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Artifact reference escapes the published repository')
    return path


def manifest(repository, version, execute_munit=False):
    validate_version(version)
    directory = repository / GROUP.replace('.', '/') / ARTIFACT / version
    jars = sorted(directory.glob('*-mule-application.jar'))
    if len(jars) != 1:
        raise ValueError('Expected exactly one Maven-published Mule application JAR')
    jar = jars[0]
    pom = directory / f'{ARTIFACT}-{version}.pom'
    if not pom.exists():
        raise ValueError('Published application POM is missing')
    tests = {'requested': execute_munit, 'executed': 0, 'skipped': not execute_munit}
    if execute_munit:
        reports = sorted(Path('target/surefire-reports').glob('TEST-*.xml'))
        for report in reports:
            root = ET.parse(report).getroot()
            tests['executed'] += int(root.get('tests', 0)) - int(root.get('skipped', 0))
            if int(root.get('failures', 0)) or int(root.get('errors', 0)):
                raise ValueError('MUnit reported failures or errors')
        if tests['executed'] != 3:
            raise ValueError('Expected evidence of exactly three executed MUnit tests')
    data = {
        'group_id': GROUP, 'artifact_id': ARTIFACT, 'version': version,
        'jar': str(jar.relative_to(repository)), 'jar_sha256': sha(jar),
        'pom': str(pom.relative_to(repository)), 'pom_sha256': sha(pom),
        'source_commit': os.environ.get('GITHUB_SHA', 'local'),
        'source_repository': os.environ.get('GITHUB_REPOSITORY', 'local'),
        'source_run_id': os.environ.get('GITHUB_RUN_ID', 'local'),
        'mule_runtime_selector': '4.9.0', 'munit_version': '3.4.0',
        'munit': tests, 'exchange_simulated': True,
    }
    (repository / 'release.json').write_text(json.dumps(data, indent=2) + '\n')
    print(f"Published selector: {GROUP}:{ARTIFACT}:{version}")
    print('Application JAR SHA-256: ' + data['jar_sha256'])
    return data


def select(repository, version, expected_run=None):
    data = json.loads((repository / 'release.json').read_text())
    if (data['group_id'], data['artifact_id'], data['version']) != (GROUP, ARTIFACT, validate_version(version)):
        raise ValueError('Published coordinates do not match requested coordinates')
    if expected_run and data['source_run_id'] != expected_run:
        raise ValueError('Published artifact is from a different workflow run')
    expected_repo = os.environ.get('GITHUB_REPOSITORY')
    if expected_repo and data['source_repository'] != expected_repo:
        raise ValueError('Published artifact belongs to a different repository')
    for name in ['jar', 'pom']:
        if sha(inside(repository, data[name])) != data[name + '_sha256']:
            raise ValueError(f'{name.upper()} checksum mismatch')
    return data, inside(repository, data['jar'])


@contextlib.contextmanager
def simulated_runtime(jar):
    # Read the real packaged fixture. This Python service is NOT a Mule runtime.
    with zipfile.ZipFile(jar) as archive:
        names = [n for n in archive.namelist() if n.split('/')[-1] == 'timetable.json']
        if len(names) != 1:
            raise ValueError('Application JAR must contain one timetable.json fixture')
        sessions = json.loads(archive.read(names[0]))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path == '/health':
                value = {'status': 'UP', 'runtime': 'python-stand-in'}
            elif parsed.path == '/timetable':
                day = urllib.parse.parse_qs(parsed.query).get('day', ['monday'])[0]
                value = [s for s in sessions if s['day'] == day]
            else:
                self.send_error(404)
                return
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def deploy(repository, version, environment, expected_run=None, require_secret=False):
    if environment not in ['DEV', 'SIT', 'UAT', 'PROD']:
        raise ValueError('Unknown simulated environment')
    token_present = bool(os.environ.get('DEMO_TOKEN'))
    if require_secret and not token_present:
        raise ValueError('DEMO_TOKEN is required but not configured')
    data, jar = select(repository, version, expected_run)
    with simulated_runtime(jar) as url:
        def get(path):
            with urllib.request.urlopen(url + path, timeout=5) as response:
                return json.load(response)
        if get('/health')['status'] != 'UP':
            raise ValueError('Health check failed')
        if get('/timetable?day=monday')[0]['id'] != 'demo-101':
            raise ValueError('Synthetic timetable smoke check failed')
        if get('/timetable?day=not-a-day') != []:
            raise ValueError('Empty-day smoke check failed')
    receipt = dict(data, environment=environment, deployment_simulated=True,
                   mule_runtime_executed=False, smoke_checks=3,
                   secret_supplied=token_present, rebuilt=False)
    output = Path('receipts')
    output.mkdir(exist_ok=True)
    (output / f'{environment}.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(f"{environment}: selected {GROUP}:{ARTIFACT}:{version}; no rebuild")
    print('Verified published JAR SHA-256: ' + data['jar_sha256'])
    print('Three HTTP checks passed against the local Python runtime stand-in')
    print('DEMO_TOKEN supplied: ' + ('yes; value not logged' if token_present else 'no'))
    if path := os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(path, 'a') as summary:
            summary.write(f"## {environment} — simulated CloudHub deployment\n\n")
            summary.write(f"Selected **{GROUP}:{ARTIFACT}:{version}** from build run {data['source_run_id']}.\n\n")
            summary.write(f"JAR SHA-256: `{data['jar_sha256']}`\n\n")
            summary.write('No rebuild. Three HTTP checks passed on a Python stand-in. **This deployment job does not start a Mule runtime or deploy to CloudHub.**\n\n')
            summary.write('MUnit: ' + (f"{data['munit']['executed']} executed" if data['munit']['requested'] else 'skipped, preserving the delivery baseline') + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['set-version', 'manifest', 'deploy'])
    parser.add_argument('--version', required=True)
    parser.add_argument('--repository', type=Path, default=Path('demo-exchange'))
    parser.add_argument('--environment', default='DEV')
    parser.add_argument('--source-run')
    parser.add_argument('--execute-munit', choices=['true', 'false'], default='false')
    parser.add_argument('--require-secret', choices=['true', 'false'], default='false')
    args = parser.parse_args()
    if args.command == 'set-version':
        set_version(args.version)
    elif args.command == 'manifest':
        manifest(args.repository, args.version, args.execute_munit == 'true')
    else:
        deploy(args.repository, args.version, args.environment, args.source_run, args.require_secret == 'true')


if __name__ == '__main__':
    main()

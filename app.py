"""A tiny build-and-deploy example. Deployments only write local JSON receipts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil


def build(message, release, destination=Path('dist')):
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', release):
        raise ValueError('Use a release such as 1.0.0')
    if not message.strip() or len(message) > 120:
        raise ValueError('Message must contain 1 to 120 characters')
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(__file__, destination / 'app.py')
    metadata = {'release': release, 'message': message, 'python': platform.python_version()}
    (destination / 'application.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return metadata


def deploy(artifact_dir, target, require_secret=False, token=None, destination=Path('deployment')):
    if target not in ('dev', 'test', 'staging'):
        raise ValueError('Choose dev, test or staging')
    if require_secret and not token:
        raise ValueError('DEMO_TOKEN is missing; add a repository Actions secret')
    artifact = artifact_dir / 'application.json'
    metadata = json.loads(artifact.read_text())
    receipt = {
        'release': metadata['release'], 'target': target,
        'build_python': metadata['python'],
        'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
        'secret_supplied': bool(token), 'simulated': True,
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    # Never print the token, its length, or any transformation of it.
    print(f"Simulated deployment: {receipt['release']} -> {target}")
    print('DEMO_TOKEN supplied: ' + ('yes (value not logged)' if token else 'no (optional for this run)'))
    if summary := os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(summary, 'a') as stream:
            stream.write('## Simulated deployment\n\n')
            stream.write('| Release | Target | Build Python | Secret supplied |\n|---|---|---|---|\n')
            stream.write(f"| {receipt['release']} | {target} | {metadata['python']} | {bool(token)} |\n")
            stream.write('\nNo external system was changed.\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    package = sub.add_parser('build')
    package.add_argument('--message', default='Hello from GitHub Actions')
    package.add_argument('--release', default='1.0.0')
    delivery = sub.add_parser('deploy')
    delivery.add_argument('--artifact-dir', type=Path, default=Path('dist'))
    delivery.add_argument('--target', default='dev')
    delivery.add_argument('--require-secret', choices=['true', 'false'], default='false')
    args = parser.parse_args()
    if args.command == 'build':
        metadata = build(args.message, args.release)
        print('Built release ' + metadata['release'])
    else:
        deploy(args.artifact_dir, args.target, args.require_secret == 'true', os.environ.get('DEMO_TOKEN'))


if __name__ == '__main__':
    main()

"""Install Maven 3.8.7 into a temporary directory; verify Apache's SHA-512."""
import hashlib
import os
from pathlib import Path
import tarfile
import urllib.request

version = '3.8.7'
base = f'https://archive.apache.org/dist/maven/maven-3/{version}/binaries/'
name = f'apache-maven-{version}-bin.tar.gz'
root = Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'mule-demo-maven'
root.mkdir(parents=True, exist_ok=True)
archive = root / name
with urllib.request.urlopen(base + name, timeout=120) as response:
    archive.write_bytes(response.read())
with urllib.request.urlopen(base + name + '.sha512', timeout=30) as response:
    expected = response.read().decode().split()[0]
if hashlib.sha512(archive.read_bytes()).hexdigest() != expected:
    raise SystemExit('Maven archive checksum failed')
with tarfile.open(archive) as tar:
    tar.extractall(root, filter='data')
bin_path = str(root / f'apache-maven-{version}' / 'bin')
with open(os.environ['GITHUB_PATH'], 'a') as output:
    output.write(bin_path + '\n')
print('Installed checksum-verified Maven ' + version)

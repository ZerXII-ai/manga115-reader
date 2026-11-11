#!/usr/bin/env python3
"""Create private local configuration without putting credentials in process arguments."""
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.env'
CONFIG = ROOT / 'config/rclone/rclone.conf'

if sys.argv[1:] == ['--show-password']:
    if not ENV.is_file():
        raise SystemExit('Run ./setup.sh first.')
    values = dict(line.split('=', 1) for line in ENV.read_text().splitlines() if '=' in line)
    print(values['OPENLIST_ADMIN_PASSWORD'])
    raise SystemExit(0)
if sys.argv[1:]:
    raise SystemExit('Usage: setup.py [--show-password]')
if ENV.exists() or CONFIG.exists():
    raise SystemExit('Existing local configuration found; it was not overwritten.')
docker = os.environ.get('MANGA_DOCKER') or shutil.which('docker')
if not docker:
    for candidate in (Path.home()/'.orbstack/bin/docker', Path('/Applications/OrbStack.app/Contents/MacOS/xbin/docker')):
        if os.access(candidate, os.X_OK):
            docker = str(candidate)
            break
if not docker:
    raise SystemExit('Docker was not found; install and start OrbStack or Docker first.')

os.umask(0o077)
for directory in (ROOT/'data/openlist', ROOT/'data/suwayomi/local', CONFIG.parent):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
password = secrets.token_urlsafe(24)
result = subprocess.run([docker, 'run', '--rm', '-i', 'rclone/rclone:1.76.0', 'obscure', '-'],
                        input=password+'\n', capture_output=True, text=True, check=True)
obscured = result.stdout.strip()
if not obscured or '\n' in obscured:
    raise SystemExit('Could not create rclone credentials.')
env = (f'HOST_UID={os.getuid()}\nHOST_GID={os.getgid()}\n'
       f'OPENLIST_ADMIN_PASSWORD={password}\n')
config = ('[manga]\ntype = webdav\nurl = http://openlist:5244/dav\n'
          f'vendor = other\nuser = admin\npass = {obscured}\n')
try:
    with CONFIG.open('x') as handle:
        handle.write(config)
    with ENV.open('x') as handle:
        handle.write(env)
except Exception:
    # Do not overwrite or remove any pre-existing configuration.
    raise
print('Local configuration created. Run ./manga.sh password to view the OpenList password privately.')
print('Next: ./manga.sh start-openlist, then configure the 115 Open storage in OpenList.')

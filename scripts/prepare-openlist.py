#!/usr/bin/env python3
"""Prepare a pinned upstream checkout and verified frontend for the local image."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/openlist'
TARGET = BUILD / 'source'
PATCH = BUILD / 'openlist-v4.2.9.patch'
COMMIT = '0497ee853853eff5fc0ada9f21684a990887de83'
GIT_URL = os.environ.get('OPENLIST_SOURCE_URL', 'https://github.com/OpenListTeam/OpenList.git')
FRONTEND_URL = 'https://github.com/OpenListTeam/OpenList-Frontend/releases/download/v4.2.9/openlist-frontend-dist-v4.2.9.tar.gz'
FRONTEND_SHA = 'b147ff4e6c6eee5dda5785a6c3028d9896ee7522a2c66c404dd7ba97fb4e78ed'
FRONTEND_SIZE = 23291965

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def git(*args, cwd=None, capture=False):
    return subprocess.run(['git', *args], cwd=cwd, check=True,
                          stdout=subprocess.PIPE if capture else None, text=True)

def validate_existing(source, marker):
    expected = {'commit': COMMIT, 'patch_sha256': sha256(PATCH), 'frontend_sha256': FRONTEND_SHA}
    try:
        info = json.loads(marker.read_text())
        head = git('rev-parse', 'HEAD', cwd=source, capture=True).stdout.strip()
        if info != expected or head != COMMIT or not (source / 'public/dist/index.html').is_file():
            return False
        git('apply', '--reverse', '--check', str(PATCH), cwd=source, capture=True)
        return True
    except (OSError, ValueError, subprocess.CalledProcessError):
        return False

def unpack_frontend(archive, destination):
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError('Unexpected path or link in frontend archive')
        tar.extractall(destination)

def main():
    if TARGET.exists():
        if validate_existing(TARGET, TARGET / '.manga-prepared.json'):
            print('Pinned OpenList source and local patch already prepared.', flush=True)
            return
        raise SystemExit('Existing build/openlist/source does not match; it was not overwritten.')
    BUILD.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.openlist-prepare-', dir=BUILD) as temp:
        tmp = Path(temp)
        source = tmp / 'source'
        print('Cloning the pinned official OpenList source.', flush=True)
        git('clone', '--depth', '1', '--branch', 'v4.2.9', '--', GIT_URL, str(source))
        if git('rev-parse', 'HEAD', cwd=source, capture=True).stdout.strip() != COMMIT:
            raise SystemExit('OpenList tag does not match the pinned commit.')
        git('apply', '--check', str(PATCH), cwd=source)
        git('apply', str(PATCH), cwd=source)
        archive = tmp / 'frontend.tar.gz'
        local_archive = os.environ.get('OPENLIST_FRONTEND_ARCHIVE')
        if local_archive:
            shutil.copyfile(local_archive, archive)
        else:
            print('Downloading the official OpenList frontend (about 23 MB).', flush=True)
            request = urllib.request.Request(FRONTEND_URL, headers={'User-Agent': 'manga-reader-bootstrap/1'})
            with urllib.request.urlopen(request, timeout=120) as response, archive.open('wb') as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
        if archive.stat().st_size != FRONTEND_SIZE or sha256(archive) != FRONTEND_SHA:
            raise SystemExit('OpenList frontend size or checksum does not match; download discarded.')
        destination = source / 'public/dist'
        destination.mkdir(parents=True, exist_ok=True)
        unpack_frontend(archive, destination)
        if not (destination / 'index.html').is_file():
            raise SystemExit('Frontend archive does not contain index.html.')
        (source / '.manga-prepared.json').write_text(json.dumps({
            'commit': COMMIT, 'patch_sha256': sha256(PATCH), 'frontend_sha256': FRONTEND_SHA,
        }) + '\n')
        os.rename(source, TARGET)
    print('OpenList source, patch and frontend prepared.', flush=True)

if __name__ == '__main__':
    main()

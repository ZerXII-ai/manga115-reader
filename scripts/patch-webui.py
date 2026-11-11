#!/usr/bin/env python3
"""Preserve cover caches while avoiding stale or persistent chapter-page caches."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'data/suwayomi/webUI/sw.js'
CONFIG = ROOT / 'data/suwayomi/server.conf'
ORIGINAL_SHA = '2eb9420cbdd776088949bf35cb6cba71792d6ad11aa81bcc909a853a058b1456'
ACTIVATE = 'self.addEventListener("activate",e=>e.waitUntil(caches.delete("image-cache-chapter-pages")));'
NEW_RULE = 'e.registerRoute(({url:e})=>e.pathname.match(/\\/chapter\\/[0-9]+\\/page\\/[0-9]+/g),({request:e})=>fetch(new Request(e,{cache:"no-store"})),"GET"),'
OLD_START = 'e.registerRoute(({url:e})=>{const{pathname:n}=e;return n.match(/\\/chapter\\/[0-9]+\\/page\\/[0-9]+/g)},new e.CacheFirst({cacheName:"image-cache-chapter-pages"'
OLD_END = '}),"GET"),e.registerRoute('
FLAVOR = re.compile(r'^(server\.webUIFlavor[ \t]*=[ \t]*)(?:"?)(WEBUI|CUSTOM)(?:"?)([ \t]*(?:#[^\r\n]*)?)$', re.I | re.M)

def inspect():
    worker = WORKER.read_text()
    config = CONFIG.read_text()
    flavors = list(FLAVOR.finditer(config))
    if len(flavors) != 1:
        raise SystemExit('Unsupported WebUI flavor; no files changed.')
    flavor = flavors[0].group(2).upper()
    if worker.startswith(ACTIVATE) and NEW_RULE in worker and flavor == 'CUSTOM':
        return worker, config, True
    if hashlib.sha256(worker.encode()).hexdigest() != ORIGINAL_SHA or worker.count(OLD_START) != 1:
        raise SystemExit('WebUI worker is not the verified bundled version; no files changed.')
    start = worker.index(OLD_START)
    end = worker.index(OLD_END, start) + len('}),"GET"),')
    patched = ACTIVATE + worker[:start] + NEW_RULE + worker[end:]
    if 'cacheName:"image-cache-manga-thumbnails"' not in patched:
        raise SystemExit('Thumbnail cache rule missing; no files changed.')
    updated = FLAVOR.sub(lambda m: m.group(1) + 'CUSTOM' + m.group(3), config, count=1)
    return patched, updated, False

def atomic_write(path, contents):
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(contents)
        os.chmod(tmp, path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def verify():
    env = {}
    p = ROOT / '.env'
    if p.is_file():
        env = dict(line.split('=', 1) for line in p.read_text().splitlines() if '=' in line and not line.startswith('#'))
    port = os.environ.get('SUWAYOMI_PORT', env.get('SUWAYOMI_PORT', '4567'))
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise SystemExit('Invalid SUWAYOMI_PORT')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(45):
        try:
            with opener.open('http://127.0.0.1:' + port + '/sw.js', timeout=2) as response:
                body = response.read().decode()
            if body.startswith(ACTIVATE) and NEW_RULE in body:
                print('Patched WebUI worker is served. Reload the browser twice to activate it.')
                return
        except (OSError, UnicodeError):
            pass
        time.sleep(1)
    raise SystemExit('Could not verify the patched worker; inspect Suwayomi logs.')

def main():
    mode = sys.argv[1:] or ['--check']
    if mode == ['--verify']:
        return verify()
    if mode not in (['--check'], ['--apply']):
        raise SystemExit('Usage: patch-webui.py --check|--apply|--verify')
    worker, config, already = inspect()
    if already:
        print('The verified cache patch is already present.')
        return
    if mode == ['--check']:
        print('The bundled WebUI can be safely patched.')
        return
    backup_root = ROOT / 'backups'
    backup_root.mkdir(mode=0o700, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='webui-before-cache-fix-', dir=backup_root))
    backup.chmod(0o700)
    shutil.copy2(WORKER, backup / 'sw.js')
    shutil.copy2(CONFIG, backup / 'server.conf')
    try:
        atomic_write(WORKER, worker)
        atomic_write(CONFIG, config)
    except Exception:
        shutil.copy2(backup / 'sw.js', WORKER)
        shutil.copy2(backup / 'server.conf', CONFIG)
        raise
    print('Cache patch installed; private backup:', backup)

if __name__ == '__main__':
    main()

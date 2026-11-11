#!/usr/bin/env python3
"""Download the pinned official JAR, verify SHA-256, and never overwrite a mismatch."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT/'build/suwayomi/suwayomi.jar'
URL = 'https://github.com/Suwayomi/Suwayomi-Server/releases/download/v2.4.2366/Suwayomi-Server-v2.4.2366.jar'
EXPECTED = 'af9feb20af9d7ebe9e30769e6c6ebc7fc7ab1c447388d42e0280b1da5fe07bfd'
EXPECTED_SIZE = 182952426
HEADERS = {'User-Agent': 'manga-reader-bootstrap/1'}
CHUNK = 4 * 1024 * 1024

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

if TARGET.exists():
    if digest(TARGET) != EXPECTED:
        raise SystemExit('Existing JAR checksum differs; it was not overwritten.')
    print('Official Suwayomi JAR checksum verified.', flush=True)
    raise SystemExit(0)
TARGET.parent.mkdir(parents=True, exist_ok=True)
print('Downloading the official Suwayomi release; the JAR is approximately 174 MiB.', flush=True)
with tempfile.TemporaryDirectory(prefix='.suwayomi-download-', dir=TARGET.parent) as scratch:
    scratch = Path(scratch)
    probe = urllib.request.Request(URL, headers={**HEADERS, 'Range': 'bytes=0-0'})
    with urllib.request.urlopen(probe, timeout=60) as response:
        signed_url = response.geturl()
        match = re.fullmatch(r'bytes 0-0/(\d+)', response.headers.get('Content-Range', ''))
        size = int(match.group(1)) if response.status == 206 and match else None
        if size is not None and size != EXPECTED_SIZE:
            raise SystemExit('Official JAR size differs; download cancelled.')

    output = scratch/'suwayomi.jar'
    if size:
        count = (size + CHUNK - 1)//CHUNK
        def download(index):
            start, end = index*CHUNK, min(size, (index+1)*CHUNK)-1
            path = scratch/str(index)
            for attempt in range(4):
                try:
                    req = urllib.request.Request(signed_url, headers={**HEADERS, 'Range': f'bytes={start}-{end}'})
                    with urllib.request.urlopen(req, timeout=90) as response, path.open('wb') as out:
                        if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{size}':
                            raise RuntimeError('Unexpected HTTP range response')
                        for data in iter(lambda: response.read(256*1024), b''):
                            out.write(data)
                    if path.stat().st_size != end-start+1:
                        raise RuntimeError('Incomplete HTTP range')
                    return index
                except Exception:
                    if attempt == 3:
                        raise RuntimeError(f'Official JAR download failed for part {index+1}') from None
                    time.sleep(attempt+1)
        with ThreadPoolExecutor(max_workers=8) as pool:
            for done, future in enumerate(as_completed([pool.submit(download, i) for i in range(count)]), 1):
                future.result()
                print(f'Downloaded {done}/{count} parts', flush=True)
        with output.open('wb') as out:
            for index in range(count):
                with (scratch/str(index)).open('rb') as part:
                    for chunk in iter(lambda: part.read(1024*1024), b''):
                        out.write(chunk)
    else:
        with urllib.request.urlopen(urllib.request.Request(URL, headers=HEADERS), timeout=90) as src, output.open('wb') as out:
            received = 0
            for chunk in iter(lambda: src.read(1024*1024), b''):
                received += len(chunk)
                if received > EXPECTED_SIZE:
                    raise RuntimeError('Official JAR is larger than expected')
                out.write(chunk)
        if received != EXPECTED_SIZE:
            raise RuntimeError('Official JAR download is incomplete')
    if digest(output) != EXPECTED:
        raise SystemExit('Downloaded JAR checksum differs; download discarded.')
    os.link(output, TARGET)  # atomic and refuses an existing target
print('Downloaded and verified the official Suwayomi JAR.', flush=True)

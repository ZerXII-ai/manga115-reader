#!/usr/bin/env python3
"""Reproducible, narrow patch of verified Suwayomi v2.4.2366. Requires JDK 17+."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import warnings
import zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'suwayomi.jar'
OUTPUT = HERE.parent / 'suwayomi-rarfix.jar'
EXPECTED = 'af9feb20af9d7ebe9e30769e6c6ebc7fc7ab1c447388d42e0280b1da5fe07bfd'
CLASS = 'eu/kanade/tachiyomi/source/local/loader/RarPageLoader.class'
HELPER = 'eu/kanade/tachiyomi/source/local/loader/RarMemoryStream.class'
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED, 'Unexpected upstream jar'
jdk_bin = Path(os.environ.get('JDK_BIN', '/opt/java/openjdk/bin'))
with tempfile.TemporaryDirectory(prefix='suwayomi-rarfix-') as scratch:
    temp = Path(scratch)
    with zipfile.ZipFile(BASE) as original:
        assert not any(n.upper().endswith(('.SF', '.RSA', '.DSA')) for n in original.namelist())
        (temp / 'original.class').write_bytes(original.read(CLASS))
    subprocess.run([str(jdk_bin/'javac'), '--release', '17', '-cp', str(BASE), '-d', scratch,
                    str(HERE/'RarMemoryStream.java'), str(HERE/'PatchRarLoader.java')], check=True)
    subprocess.run([str(jdk_bin/'java'), '-cp', os.pathsep.join((scratch, str(BASE))),
                    'PatchRarLoader', str(temp/'original.class'), str(temp/'patched.class')], check=True)
    with zipfile.ZipFile(BASE) as original, zipfile.ZipFile(OUTPUT, 'w') as patched:
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='Duplicate name:')
            for entry in original.infolist():
                data = (temp/'patched.class').read_bytes() if entry.filename == CLASS else original.read(entry)
                patched.writestr(entry, data)
        helper = zipfile.ZipInfo(HELPER, (2026, 11, 10, 0, 0, 0))
        helper.compress_type = zipfile.ZIP_DEFLATED
        helper.external_attr = 0o644 << 16
        patched.writestr(helper, (temp/HELPER).read_bytes())
    with zipfile.ZipFile(BASE) as original, zipfile.ZipFile(OUTPUT) as patched:
        originals = original.infolist()
        copies = patched.infolist()
        assert [e.filename for e in copies[:-1]] == [e.filename for e in originals]
        changed = {before.filename for before, after in zip(originals, copies)
                   if original.read(before) != patched.read(after)}
        assert changed == {CLASS}, changed
        assert set(patched.namelist()) - set(original.namelist()) == {HELPER}
print(OUTPUT.name, hashlib.sha256(OUTPUT.read_bytes()).hexdigest())

#!/usr/bin/env python3
"""Apply archive page-cache recovery to the verified, already RAR-patched JAR."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import warnings
import zipfile

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'suwayomi-rarfix.jar'
OUTPUT = HERE.parent / 'suwayomi-cachefix.jar'
PAGE = 'suwayomi/tachidesk/manga/impl/Page.class'
SOURCE = 'eu/kanade/tachiyomi/source/local/LocalSource.class'
PREFIX = 'eu/kanade/tachiyomi/source/local/loader/'
HELPERS = [PREFIX + 'ArchivePageCache.class', PREFIX + 'ArchivePageCache$1.class']
# The preceding build.py verifies the pinned upstream JAR and generates this
# intermediate file. Its digest may differ across JDK and zlib versions.
jdk = Path(os.environ.get('JDK_BIN', '/opt/java/openjdk/bin'))
with tempfile.TemporaryDirectory(prefix='suwayomi-cachefix-') as scratch:
    tmp = Path(scratch)
    stub = tmp / 'stubs-src' / PREFIX
    stub.mkdir(parents=True)
    (stub/'ReaderPage.java').write_text('package eu.kanade.tachiyomi.source.local.loader; public class ReaderPage { public kotlin.jvm.functions.Function0<java.io.InputStream> getStream(){return null;} }')
    (stub/'PageLoader.java').write_text('package eu.kanade.tachiyomi.source.local.loader; public interface PageLoader { Object getPages(kotlin.coroutines.Continuation<? super java.util.List<ReaderPage>> c); void recycle(); }')
    for name in ('ZipPageLoader', 'RarPageLoader', 'EpubPageLoader'):
        (stub/(name+'.java')).write_text('package eu.kanade.tachiyomi.source.local.loader; public final class '+name+' implements PageLoader { public '+name+'(java.io.File f) {} public Object getPages(kotlin.coroutines.Continuation<? super java.util.List<ReaderPage>> c){return null;} public void recycle(){} }')
    stub_bin = tmp/'stubs'
    stub_bin.mkdir()
    subprocess.run([str(jdk/'javac'), '--release', '17', '-cp', str(BASE), '-d', str(stub_bin), *map(str, stub.glob('*.java'))], check=True)
    cp = os.pathsep.join((str(stub_bin), str(BASE)))
    subprocess.run([str(jdk/'javac'), '--release', '17', '-cp', cp, '-d', scratch,
                    *map(str, (HERE/'ArchivePageCache.java', HERE/'PatchPageCache.java', HERE/'PatchLocalSource.java'))], check=True)
    with zipfile.ZipFile(BASE) as jar:
        (tmp/'page.class').write_bytes(jar.read(PAGE))
        (tmp/'source.class').write_bytes(jar.read(SOURCE))
    for patcher, source, output in (('PatchPageCache','page.class','page-patched.class'),
                                    ('PatchLocalSource','source.class','source-patched.class')):
        subprocess.run([str(jdk/'java'), '-cp', os.pathsep.join((scratch, str(BASE))), patcher,
                        str(tmp/source), str(tmp/output)], check=True)
    changes = {PAGE:(tmp/'page-patched.class').read_bytes(), SOURCE:(tmp/'source-patched.class').read_bytes()}
    with zipfile.ZipFile(BASE) as original, zipfile.ZipFile(OUTPUT, 'w') as patched:
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='Duplicate name:')
            for entry in original.infolist():
                patched.writestr(entry, changes.get(entry.filename, original.read(entry)))
        for name in HELPERS:
            info = zipfile.ZipInfo(name, (2026, 11, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            patched.writestr(info, (tmp/name).read_bytes())
    with zipfile.ZipFile(BASE) as original, zipfile.ZipFile(OUTPUT) as patched:
        originals, copies = original.infolist(), patched.infolist()
        assert [e.filename for e in copies[:-len(HELPERS)]] == [e.filename for e in originals]
        changed = {before.filename for before, after in zip(originals, copies)
                   if original.read(before) != patched.read(after)}
        assert changed == set(changes), changed
        assert set(patched.namelist()) - set(original.namelist()) == set(HELPERS)
print(OUTPUT.name, hashlib.sha256(OUTPUT.read_bytes()).hexdigest())

#!/usr/bin/env python3
"""Verify the distributable files without opening any Telegram account."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import zipfile

root = Path(__file__).resolve().parent.parent
dist = root / 'dist'
index = json.loads((dist / 'index.json').read_text())
for entry, filename in [(index['latest_apk'], 'koteloader.apk'), (index['sdk'], 'kote-module-sdk.zip')]:
    path = dist / filename
    assert path.stat().st_size == entry['size'], filename
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], filename
version = index['latest_apk']['version_name']
assert (dist / f'koteloader-{version}.apk').read_bytes() == (dist / 'koteloader.apk').read_bytes()
assert index['sdk']['version'] == version
with zipfile.ZipFile(dist / 'koteloader.apk') as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    assert 'lib/arm64-v8a/libkotocore.so' in names
    assert 'lib/arm64-v8a/libkotosandbox.so' in names
    assert not any('/libkotomod_counter.so' in name or '/libkotomod_settings_demo.so' in name for name in names)
    assert all(name.split('/')[1] == 'arm64-v8a' for name in names if name.startswith('lib/') and name.endswith('.so'))
with zipfile.ZipFile(dist / 'kote-module-sdk.zip') as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    assert not any(name.endswith(('.keystore', '.jks', '.properties', '.so', '.o', '.a')) for name in names)
    assert not any(name.endswith(('/counter.c', '/hello.c', '/settings_demo.c')) for name in names)
    header = archive.read('kote_module_sdk/include/module_abi.h').decode()
    assert 'KOTO_CHAT_PRIVATE' in header and 'KOTO_BAN_REPORT_SPAM' in header
    assert 'kote_module_sdk/examples/native/chess.c' in names
sdk = os.environ.get('ANDROID_HOME')
if sdk:
    tools = Path(sdk) / 'build-tools/34.0.0'
    apk = dist / 'koteloader.apk'
    subprocess.run([str(tools / 'apksigner'), 'verify', str(apk)], check=True)
    badging = subprocess.check_output([str(tools / 'aapt'), 'dump', 'badging', str(apk)], text=True)
    assert re.search(r"versionCode='(\d+)'", badging)[1] == str(index['latest_apk']['version_code'])
    assert re.search(r"versionName='([^']+)'", badging)[1] == version
print(f'Distribution {version}: APK/SDK hashes, formats, versions and contents verified')

#!/usr/bin/env python3
"""Build MailCraft PortableApps staging and independently generated ZIP from patched source."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def copy_existing(source, destination):
    if not source.is_file():
        raise FileNotFoundError(f'Required upstream file missing: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def stage(source, workspace, info, revision):
    if not re.fullmatch(r'b\d+r\d+', revision):
        raise ValueError('Revision must be b<number>r<number>, for example b1r1')
    version = info['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Malformed upstream semver')
    root = workspace / 'dist' / 'stage' / 'MailCraftPortable'
    if root.exists():
        shutil.rmtree(root)
    app = root / 'App' / 'MailCraft'
    appinfo = root / 'App' / 'AppInfo'
    srcdir = root / 'Other' / 'Source'
    data = root / 'Data' / 'MailCraft'
    for dir_ in (app, appinfo, srcdir, data):
        dir_.mkdir(parents=True, exist_ok=True)
    target = source / 'target' / 'x86_64-pc-windows-msvc' / 'release'
    copy_existing(workspace / 'build' / 'MailCraftPortable.exe', root / 'MailCraftPortable.exe')
    for file in ('mailcraft.exe', 'mailcraft-cli.exe'):
        copy_existing(target / file, app / file)
    # Both binaries use this strict, in-process PortableApps marker and their own path.
    (app / 'portable.txt').write_bytes(b'')
    copy_existing(source / 'assets' / 'app-icon' / 'mailcraft.ico', appinfo / 'appicon.ico')
    for file in ('LICENSE-MIT', 'LICENSE-APACHE', 'NOTICE', 'ATTRIBUTION.md'):
        copy_existing(source / file, srcdir / file)
    # The upstream NOTICE explicitly requires bundling licenses for compiled-in fonts.
    for file in ('OFL-Inter.txt', 'OFL-SourceSans3.txt', 'OFL-JetBrainsMono.txt'):
        copy_existing(source / 'assets' / 'fonts' / file, srcdir / file)
    (srcdir / 'Portable-Attribution.txt').write_text(
        'MailCraft (C) MailCraft contributors; MIT OR Apache-2.0.\n'
        'PortableApps launcher and build adapters: community integration, MIT OR Apache-2.0.\n'
        'This is independent and not an official PortableApps.com package.\n'
        'Upstream: https://github.com/UCS-Care-Group/mailcraft\n', encoding='utf-8')
    ini = f'''[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=MailCraft Portable (Community)
AppID=MailCraftPortableCommunity
BaseAppName=MailCraft
Publisher=UCS Care Group and MailCraft contributors
Homepage=https://github.com/UCS-Care-Group/mailcraft
Category=Internet
Description=Portable mail calendar contacts and tasks client
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion={version}.0
DisplayVersion={version} ({revision})

[Control]
Icons=1
Start=MailCraftPortable.exe

[PortableApps.comInstaller]
Run=false
'''
    (appinfo / 'appinfo.ini').write_text(ini, encoding='utf-8', newline='\r\n')
    # Include application-specific metadata, source identity, lockfile fingerprint and patches.
    source_lock = source / 'Cargo.lock'
    if not source_lock.is_file():
        raise FileNotFoundError('Upstream Cargo.lock missing: locked reproducibility impossible')
    identity = {**info, 'application': 'MailCraft', 'architecture': 'windows-x64',
                'mode': 'PORTABLEAPPS', 'revision': revision,
                'builder_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=workspace,
                         capture_output=True, encoding='utf-8').stdout.strip() or '(builder checkout unavailable)',
                'cargo_lock_sha256': digest(source_lock),
                'portable_source_adaptation': 'scripts/patch.py (settings, attachments, credential store)',
                'installer_engine': 'custom-nsis',
                'shared_package_builder': 'vhick/Portable-Package-Builder@v1.0.0',
                'shared_release_publisher': 'vhick/portable-release-publisher@v1.1.1'}
    (srcdir / 'BUILD-IDENTITY.json').write_text(json.dumps(identity, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    (srcdir / 'PORTABILITY.txt').write_text(
        'Portable files: Data/MailCraft (mailbox, settings, logs, pictures, local attachments).\n'
        'Credential Manager: intentionally disabled for portable accounts; sign in again as needed.\n'
        'Windows notifications may be unavailable without installed-app shortcut identity.\n'
        'Exports and files explicitly selected by the user can be stored outside Data.\n'
        'OS-owned execution/shell caches and user-approved external application activity remain.\n'
        'Close the tray application using Quit before removing USB media.\n'
        'Do not edit or remove Data when upgrading. The shared installer preserves it.\n', encoding='utf-8')
    png = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                          '-File', str(workspace / 'scripts' / 'icons.ps1'),
                          '-Icon', str(appinfo / 'appicon.ico'), '-Destination', str(appinfo)], check=False)
    if png.returncode:
        raise RuntimeError('Could not create authentic upstream appicon_16.png / appicon_32.png')
    zip_path = workspace / 'dist' / f'MailCraftPortable_{version}_x64_{revision}.zip'
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        raise FileExistsError(f'Refusing to overwrite output: {zip_path}')
    # Put root package folder in archive, as PortableApps ZIPs conventionally do.
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=7, allowZip64=True) as zipped:
        for item in [root, *sorted(root.rglob('*'))]:
            rel = item.relative_to(root.parent).as_posix()
            if item.is_symlink():
                raise RuntimeError(f'Symlink in portable staging: {item}')
            if item.is_dir():
                zipped.writestr(rel+'/', b'')
            else:
                zipped.write(item, rel)
    print(json.dumps({'stage': str(root), 'zip': str(zip_path), 'sha256': digest(zip_path),
                      'source': identity}, indent=2, ensure_ascii=False))
    return root, zip_path


if __name__ == '__main__':
    arg = argparse.ArgumentParser()
    arg.add_argument('--source', type=Path, required=True)
    arg.add_argument('--workspace', type=Path, required=True)
    arg.add_argument('--identity', type=Path, required=True)
    arg.add_argument('--revision', default='b1r1')
    a = arg.parse_args()
    stage(a.source.resolve(), a.workspace.resolve(), json.loads(a.identity.read_text(encoding='utf-8')), a.revision)

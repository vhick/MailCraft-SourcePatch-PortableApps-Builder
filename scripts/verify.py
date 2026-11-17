#!/usr/bin/env python3
"""Static Windows PE, icon, staging, metadata and ZIP validation. Not a GUI test."""
import argparse
import configparser
import hashlib
from pathlib import Path
import struct
import zipfile


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def pe(path, machine=0x8664, subsystem=None):
    data = path.read_bytes()
    if len(data) < 512 or data[:2] != b'MZ':
        raise ValueError(f'Not a Windows PE: {path}')
    off = struct.unpack_from('<I', data, 0x3c)[0]
    if off < 64 or off + 256 > len(data) or data[off:off+4] != b'PE\0\0':
        raise ValueError(f'Invalid PE signature: {path}')
    found = struct.unpack_from('<H', data, off+4)[0]
    if found != machine:
        raise ValueError(f'Wrong PE architecture for {path.name}: {found:#x}')
    if subsystem is not None:
        optional_header_magic = struct.unpack_from('<H', data, off+24)[0]
        if optional_header_magic != 0x20b:
            raise ValueError(f'Expected PE32+ optional header: {path.name}')
        actual = struct.unpack_from('<H', data, off+24+0x44)[0]
        if actual != subsystem:
            raise ValueError(f'Wrong Windows subsystem for {path.name}: {actual}')


def ico(icon):
    data = icon.read_bytes()
    if len(data) < 6 or data[:4] != b'\0\0\x01\0':
        raise ValueError('Invalid upstream ICO')
    n = struct.unpack_from('<H', data, 4)[0]
    frames = {(256 if data[6+i*16] == 0 else data[6+i*16]) for i in range(n) if 6+(i+1)*16 <= len(data)}
    if not {16, 32}.issubset(frames):
        raise ValueError('ICO lacks required 16/32px frames; do not synthesize or substitute a logo')


def verify(root, archive):
    if root.name != 'MailCraftPortable':
        raise ValueError('Wrong package root folder')
    need = [root/'MailCraftPortable.exe', root/'App'/'MailCraft'/'mailcraft.exe',
            root/'App'/'MailCraft'/'mailcraft-cli.exe', root/'App'/'MailCraft'/'portable.txt',
            root/'App'/'AppInfo'/'appinfo.ini', root/'App'/'AppInfo'/'appicon.ico',
            root/'App'/'AppInfo'/'appicon_16.png', root/'App'/'AppInfo'/'appicon_32.png',
            root/'Other'/'Source'/'BUILD-IDENTITY.json', root/'Data'/'MailCraft']
    for file in need:
        if not file.exists():
            raise FileNotFoundError(f'Missing package component: {file}')
    if (root/'App'/'MailCraft'/'portable.txt').stat().st_size:
        raise ValueError('Portable marker must be empty')
    pe(root/'MailCraftPortable.exe', subsystem=2)
    pe(root/'App'/'MailCraft'/'mailcraft.exe', subsystem=2)
    pe(root/'App'/'MailCraft'/'mailcraft-cli.exe', subsystem=3)
    ico(root/'App'/'AppInfo'/'appicon.ico')
    config = configparser.ConfigParser(interpolation=None)
    config.read(root/'App'/'AppInfo'/'appinfo.ini', encoding='utf-8')
    if (config.get('Format','Type') != 'PortableApps.comFormat' or
        config.get('Details','AppID') != 'MailCraftPortableCommunity' or
        config.get('Control','Start') != 'MailCraftPortable.exe'):
        raise ValueError('Invalid PortableApps metadata')
    if any((root/'Data').rglob('*')):
        for entry in (root/'Data').rglob('*'):
            if entry.is_file():
                raise ValueError('Staging Data must not contain user files')
    actual = {}
    for file in root.rglob('*'):
        if file.is_symlink():
            raise ValueError('Forbidden symlink in package')
        if file.is_file():
            actual[f'{root.name}/{file.relative_to(root).as_posix()}'] = sha(file)
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        raise ValueError('PortableApps ZIP missing or damaged')
    with zipfile.ZipFile(archive) as zipfile_:
        entries = {}
        for item in zipfile_.infolist():
            name = item.filename
            if name.startswith('/') or '\\' in name or '..' in name.split('/'):
                raise ValueError(f'Unsafe archive entry: {name}')
            if item.is_dir():
                continue
            if name in entries:
                raise ValueError(f'Duplicate ZIP entry: {name}')
            h = hashlib.sha256()
            with zipfile_.open(item) as f:
                for b in iter(lambda:f.read(1024*1024), b''):
                    h.update(b)
            entries[name] = h.hexdigest()
    if entries != actual:
        raise ValueError('ZIP and staging file list/hashes differ')
    print('STATIC-VALIDATED: x64 PE launcher/app/CLI, ZIP paths/hashes, metadata/icons, data containment staging')
    print(f'ZIP SHA256: {sha(archive)}  {archive.name}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--stage', required=True, type=Path)
    p.add_argument('--zip', required=True, type=Path)
    a = p.parse_args()
    verify(a.stage.resolve(), a.zip.resolve())

#!/usr/bin/env python3
"""Verified, short-lived upstream checkout for a Windows source build.

Clone without creating any working-tree files, activate a narrowly scoped
sparse-checkout exclusion for unrelated Android screenshot *test fixtures*,
then check out the *verified* immutable tag commit.  Git's Windows long-path
setting is repository local, never a machine-wide registry/config change.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess

UPSTREAM_REPO = 'https://github.com/UCS-Care-Group/mailcraft.git'
SKIPPED_FIXTURES = '!/apps/mailcraft-android/app/src/test/snapshots/images/'
SOURCE_REQUIRED = ('Cargo.toml', 'Cargo.lock', 'crates/net/src/oauth.rs',
                   'crates/ui-egui/src/lib.rs', 'apps/mailcraft/src/main.rs')


def _git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(['git', *args], cwd=cwd, check=True,
                            text=True, encoding='utf-8', errors='replace',
                            capture_output=True)
    return result.stdout.strip()


def checkout(tag: str, sha: str, destination: Path, repo: str = UPSTREAM_REPO) -> None:
    if not re.fullmatch(r'v?(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)', tag):
        raise ValueError('Invalid stable upstream tag (expected vX.Y.Z)')
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Invalid resolved upstream commit SHA')
    if destination.exists():
        raise RuntimeError(f'Checkout destination already exists: {destination}')
    # Don't let a failure leave a partly checked-out copy to build by mistake.
    try:
        _git('-c', 'core.longpaths=true', 'clone', '--depth', '1', '--single-branch',
             '--branch', tag, '--no-checkout', repo, str(destination))
        _git('config', '--local', 'core.longpaths', 'true', cwd=destination)
        # / * selects all source recursively. Exclude ONLY optional Android test
        # screenshot fixtures. Do NOT exclude Rust crates or Windows assets.
        _git('sparse-checkout', 'set', '--no-cone', '/*', SKIPPED_FIXTURES,
             cwd=destination)
        _git('checkout', '--detach', '--force', sha, cwd=destination)
        got = _git('rev-parse', 'HEAD', cwd=destination)
        if got != sha:
            raise RuntimeError(f'Tag checkout resolved to {got}, expected {sha}')
        tag_sha = _git('rev-parse', f'refs/tags/{tag}^{{commit}}', cwd=destination)
        if tag_sha != sha:
            raise RuntimeError(f'Upstream tag points at {tag_sha}, not {sha}')
        missing = [name for name in SOURCE_REQUIRED if not (destination / name).is_file()]
        if missing:
            raise RuntimeError('Required upstream source missing after checkout: ' + ', '.join(missing))
        if (destination / 'apps/mailcraft-android/app/src/test/snapshots/images').exists():
            raise RuntimeError('Android snapshot fixture exclusion did not take effect')
        print(f'VERIFIED: {tag} -> {sha} (sparse checkout excludes only Android snapshot images)')
    except BaseException:
        if destination.exists():
            shutil.rmtree(destination)
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--tag', required=True)
    p.add_argument('--sha', required=True)
    p.add_argument('--destination', type=Path, required=True)
    a = p.parse_args()
    checkout(a.tag, a.sha, a.destination)

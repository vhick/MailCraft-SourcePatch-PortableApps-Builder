#!/usr/bin/env python3
"""Reserve an application-specific release identity and skip duplicate successful builds."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

MARKER = '<!-- portable-release-publisher:managed:v2 -->'


def preflight(info, revision, env_file):
    if not re.fullmatch(r'b\d+r\d+', revision):
        raise ValueError('Unsafe package revision (expected b1r1-style)')
    builder = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True,
                             encoding='utf-8', check=True).stdout.strip()
    tag = f'mailcraft-portable-v{info["version"]}-{revision}-u{info["commit"][:8]}-b{builder[:8]}'
    repo = os.environ['GITHUB_REPOSITORY']
    call = subprocess.run(['gh', 'release', 'view', tag, '--repo', repo,
                           '--json', 'body,assets,isDraft,tagName'], capture_output=True, encoding='utf-8')
    skip = False
    if call.returncode == 0:
        result = json.loads(call.stdout)
        if result.get('isDraft') or MARKER not in result.get('body', ''):
            raise RuntimeError(f'Existing tag is not a complete publisher-managed release: {tag}')
        names = {asset['name'] for asset in result.get('assets', [])}
        if not any(n.endswith('.zip') for n in names) or not any(n.endswith('.paf.exe') for n in names) or 'SHA256SUMS.txt' not in names:
            raise RuntimeError('Existing ZIP-only or incomplete release detected. Select a new package revision to retry safely.')
        skip = True
    else:
        error = call.stderr.lower()
        if not any(s in error for s in ('not found', 'http 404', 'release not found')):
            raise RuntimeError(f'Release preflight failed, not treating as missing: {call.stderr}')
    with env_file.open('a', encoding='utf-8') as f:
        f.write(f'RELEASE_TAG={tag}\nALREADY_PUBLISHED={str(skip).lower()}\n')
    print(f'Release tag: {tag}; already completed: {skip}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--identity', type=Path, required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--github-env', type=Path, required=True)
    a = p.parse_args()
    preflight(json.loads(a.identity.read_text(encoding='utf-8')), a.revision, a.github_env)

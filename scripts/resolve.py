#!/usr/bin/env python3
"""Resolve the highest suitable published stable MailCraft tag, then its immutable commit."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = 'UCS-Care-Group/mailcraft'
STABLE = re.compile(r'^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')


def api(path):
    req = urllib.request.Request('https://api.github.com' + path,
        headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'MailCraftPortable-Builder-b1r1',
                 **({'Authorization': 'Bearer ' + os.environ['GH_TOKEN']} if os.getenv('GH_TOKEN') else {})})
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError('GitHub API resource not found (404): ' + path) from e
        raise RuntimeError(f'GitHub API failure HTTP {e.code} on {path}: {e.reason}') from e


def stable_version(tag):
    match = STABLE.fullmatch(tag)
    return tuple(map(int, match.groups())) if match else None


def tag_commit(tag):
    # Git refs may point to either a commit (lightweight) or annotated tag object.
    ref = api('/repos/' + REPO + '/git/ref/tags/' + urllib.parse.quote(tag, safe=''))
    item = ref['object']
    for _ in range(6):
        if item['type'] == 'commit':
            sha = item['sha']
            if not re.fullmatch(r'[a-f0-9]{40}', sha):
                raise RuntimeError('Unexpected tag target SHA')
            return sha
        if item['type'] != 'tag':
            raise RuntimeError('Unsupported tag target: ' + str(item['type']))
        item = api('/repos/' + REPO + '/git/tags/' + item['sha'])['object']
    raise RuntimeError('Tag is nested too deeply')


def resolve(requested):
    if requested.lower() == 'latest':
        # Explicit numeric sort: the GitHub API does not guarantee semantic ordering.
        releases = []
        for page in range(1, 4):
            batch = api(f'/repos/{REPO}/releases?per_page=100&page={page}')
            if not isinstance(batch, list):
                raise RuntimeError('Unexpected releases response type')
            releases.extend(batch)
            if len(batch) < 100:
                break
        candidates = [(stable_version(r.get('tag_name', '')), r) for r in releases
                      if not r.get('draft') and not r.get('prerelease') and stable_version(r.get('tag_name', ''))]
        if not candidates:
            raise RuntimeError('No published, semver-stable MailCraft GitHub release found')
        _, chosen = max(candidates, key=lambda item: item[0])
    else:
        if stable_version(requested) is None:
            raise ValueError('Request vX.Y.Z (stable only) or latest')
        chosen = api(f'/repos/{REPO}/releases/tags/{urllib.parse.quote(requested, safe="")}')
        if chosen.get('draft') or chosen.get('prerelease') or stable_version(chosen.get('tag_name', '')) is None:
            raise ValueError('Requested release is not a published stable release')
    tag = chosen['tag_name']
    result = {'upstream_repository': 'https://github.com/' + REPO,
              'version': '.'.join(map(str, stable_version(tag))), 'tag': tag,
              'commit': tag_commit(tag), 'release_id': chosen['id'], 'release_url': chosen['html_url']}
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--requested', default='latest')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    obj = resolve(a.requested)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(obj, indent=2))

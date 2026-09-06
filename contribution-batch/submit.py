#!/usr/bin/env python
"""Submit the reviewed SD.Next branches using an existing GitHub CLI login.

Default: read-only preflight. Pass --submit to open missing upstream PRs.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parent


def run(*args):
    result = subprocess.run(['gh', *args], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def api(path):
    return json.loads(run('api', '--hostname', 'github.com', path))


def existing_prs(manifest, entry):
    query = urlencode({
        'state': 'all', 'base': manifest['base'],
        'head': f"{manifest['owner']}:{entry['branch']}", 'per_page': 100,
    })
    return api(f"repos/{manifest['repository']}/pulls?{query}")


def verify_heads(manifest, entry):
    upstream = api(f"repos/{manifest['repository']}/git/ref/heads/{manifest['base']}")['object']['sha']
    head = api(f"repos/{manifest['fork']}/git/ref/heads/{entry['branch']}")['object']['sha']
    if upstream != manifest['verified_base'] or head != entry['head_sha']:
        raise RuntimeError(f"Reviewed source changed for {entry['branch']}; refresh and retest before submission")


def verify_body(entry):
    body_file = ROOT / entry['body_file']
    content = body_file.read_bytes()
    if (not content.startswith(b'AI-authored note:')
            or hashlib.sha256(content).hexdigest() != entry['body_sha256']):
        raise RuntimeError(f"PR description changed since preparation: {body_file}")
    return body_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submit', action='store_true', help='Open missing PRs after all preflight checks pass')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))

    run('auth', 'status', '--hostname', 'github.com')
    login = api('user')['login']
    if login.lower() != manifest['owner'].lower():
        raise RuntimeError(f"Expected GitHub login {manifest['owner']}, found {login}; no PRs created")

    # Submission should use the exact upstream source that passed review/tests.
    upstream = api(f"repos/{manifest['repository']}/git/ref/heads/{manifest['base']}")['object']['sha']
    if upstream != manifest['verified_base']:
        raise RuntimeError('Upstream dev changed. Refresh affected branches and rerun their tests before submission; no PRs created')

    ready = []
    for entry in manifest['pull_requests']:
        head = api(f"repos/{manifest['fork']}/git/ref/heads/{entry['branch']}")['object']['sha']
        if head != entry['head_sha']:
            raise RuntimeError(f"Branch changed since review: {entry['branch']}; no PRs created")
        comparison = api(f"repos/{manifest['fork']}/compare/{manifest['verified_base']}...{head}")
        actual = sorted(item['filename'] for item in comparison['files'])
        if (actual != sorted(entry['files']) or comparison['ahead_by'] != 1
                or comparison['behind_by'] != 0):
            raise RuntimeError(f"Unexpected diff in {entry['branch']}; no PRs created")
        verify_body(entry)
        matches = existing_prs(manifest, entry)
        if matches:
            for match in matches:
                print(f"EXISTING ({match['state']}): {match['html_url']}")
            continue
        ready.append(entry)
        print(f"READY: {entry['title']}")

    if not args.submit:
        print(f'Preflight passed: {len(ready)} missing PRs. Run again with --submit to open them.')
        return

    for entry in ready:
        # Recheck just before each write, so reruns or another agent do not duplicate PRs.
        matches = existing_prs(manifest, entry)
        if matches:
            print(f"EXISTING: {matches[0]['html_url']}")
            continue
        verify_heads(manifest, entry)
        body_file = verify_body(entry)
        print(run(
            'pr', 'create', '--repo', f"https://github.com/{manifest['repository']}", '--base', manifest['base'],
            '--head', f"{manifest['owner']}:{entry['branch']}", '--title', entry['title'],
            '--body-file', str(body_file),
        ))
        receipts = existing_prs(manifest, entry)
        expected_body = body_file.read_text(encoding='utf-8').replace('\r\n', '\n').rstrip()
        verified = any(
            item.get('head', {}).get('sha') == entry['head_sha']
            and item.get('head', {}).get('ref') == entry['branch']
            and item.get('head', {}).get('repo', {}).get('full_name') == manifest['fork']
            and item.get('base', {}).get('ref') == manifest['base']
            and item.get('base', {}).get('repo', {}).get('full_name') == manifest['repository']
            and item.get('title') == entry['title']
            and (item.get('body') or '').replace('\r\n', '\n').rstrip() == expected_body
            for item in receipts
        )
        if not verified:
            raise RuntimeError('PR command completed but its expected payload was not verified; inspect the printed URL before retrying')


if __name__ == '__main__':
    main()

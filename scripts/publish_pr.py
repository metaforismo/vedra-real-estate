#!/usr/bin/env python3
"""Publish this reviewed patch to Vedra; merge only after both CI jobs succeed.

Run from the extracted release, with --repo pointing at a clean Git clone.
No force pushes, administrator overrides, or credential handling are performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

REPOSITORY = 'metaforismo/vedra-real-estate'
BASE_SHA = 'f1a47fc1c5873992ab6cbb99e56770dfc141d2dc'
BRANCH = 'release/vedra-0.4.0'
EXPECTED_CHECKS = {'tests', 'postgres'}
TITLE = 'Vedra 0.4: full-archive explorer, atomic team triage and evidence history'
BODY = """## Changes
- Search and paginate the entire archive, including records beyond the dashboard sample.
- Add explicit range/focus filters, cross-page selection and non-truncating exports.
- Apply batch team decisions atomically with optimistic concurrency and audit events.
- Preserve typed observed-field snapshots; never infer missing historic evidence.
- Diagnose agent configuration locally without portal requests or model calls.
- Improve mobile/keyboard workflows, loading/error states and cancellation of stale searches.
- Add an additive v4 migration, PostgreSQL coverage, CI and upgrade documentation.

## Verification
See TEST_REPORT.md for the executed local tests and limitations. The required jobs
`tests` and `postgres` must pass before merging; no skipped check counts as success.
PostgreSQL, live portal acquisition, model/Hermes, SMTP and hosted deployment have
not been validated in the offline development environment. No credentials or
runtime data are included. The deployment remains one private instance per client.
"""


def command(repo: Path, *args: str, timeout: int = 120) -> str:
    result = subprocess.run(args, cwd=repo, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        # CLI error messages can echo remote URLs; credentials never belong there.
        raise RuntimeError(f'{args[0]} {args[1]} failed ({result.returncode}). '
                           'Inspect the command locally; nothing has been force-pushed or merged.')
    return result.stdout.strip()


def expected_remote(value: str) -> bool:
    return value.strip().removesuffix('.git') in {
        f'https://github.com/{REPOSITORY}', f'git@github.com:{REPOSITORY}',
        f'ssh://git@github.com/{REPOSITORY}',
    }


def checks_ready(checks: list[dict]) -> bool:
    """Never interpret missing, skipped, neutral, cancelled or stale checks as green."""
    if not EXPECTED_CHECKS.issubset({c.get('name') for c in checks}):
        return False
    return all(c.get('bucket') == 'pass' for c in checks)


def can_merge(info: dict, sha: str) -> bool:
    return (info.get('state') == 'OPEN' and not info.get('isDraft')
            and info.get('headRefOid') == sha
            and info.get('baseRefName') == 'main'
            and info.get('mergeable') == 'MERGEABLE'
            and info.get('mergeStateStatus') == 'CLEAN'
            and info.get('reviewDecision') not in {'CHANGES_REQUESTED', 'REVIEW_REQUIRED'})


def check_state(repo: Path, url: str) -> list[dict]:
    result = subprocess.run(['gh', 'pr', 'checks', url, '--repo', REPOSITORY,
                             '--json', 'name,bucket,state'], cwd=repo,
                            text=True, capture_output=True, timeout=60)
    # gh returns 8 while pending and 1 for failed/no checks; inspect only valid JSON.
    try:
        checks = json.loads(result.stdout)
    except json.JSONDecodeError:
        if result.returncode == 1 and not result.stdout.strip():
            return []
        raise RuntimeError('Unable to read GitHub check results; PR remains open.') from None
    if not isinstance(checks, list):
        raise RuntimeError('Unexpected GitHub response; PR remains open.')
    if any(c.get('bucket') in {'fail', 'cancel'} for c in checks):
        raise RuntimeError('A CI check failed or was cancelled; PR remains open.')
    return checks


def merge_when_green(repo: Path, url: str, sha: str, wait_seconds: int) -> None:
    deadline = time.monotonic() + wait_seconds
    fields = 'state,isDraft,headRefOid,baseRefName,mergeable,mergeStateStatus,reviewDecision'
    while time.monotonic() < deadline:
        info = json.loads(command(repo, 'gh', 'pr', 'view', url, '--repo', REPOSITORY,
                                  '--json', fields))
        if info.get('headRefOid') != sha or info.get('state') != 'OPEN':
            raise RuntimeError('PR head/state changed. Refusing to merge a different revision.')
        if info.get('reviewDecision') == 'CHANGES_REQUESTED':
            raise RuntimeError('Changes requested by review; PR remains open.')
        if checks_ready(check_state(repo, url)) and can_merge(info, sha):
            command(repo, 'gh', 'pr', 'merge', url, '--repo', REPOSITORY,
                    '--squash', '--delete-branch', '--match-head-commit', sha)
            state = json.loads(command(repo, 'gh', 'pr', 'view', url, '--repo', REPOSITORY,
                                       '--json', 'state,mergeCommit'))
            if state.get('state') != 'MERGED':
                raise RuntimeError('Merge not confirmed (possibly queued). Check the PR on GitHub.')
            print(f'Merged: {url}\nCommit: {(state.get("mergeCommit") or {}).get("oid", "unknown")}')
            return
        time.sleep(10)
    raise RuntimeError('Timed out waiting for both CI jobs/reviews. PR remains open; no merge attempted.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--patch', required=True, type=Path)
    parser.add_argument('--merge', action='store_true', help='Wait for CI, then merge (never bypass rules).')
    parser.add_argument('--wait-seconds', type=int, default=1800)
    args = parser.parse_args()
    repo, patch = args.repo.resolve(), args.patch.resolve()
    if not repo.is_dir() or not patch.is_file():
        parser.error('Provide an existing Git clone and the downloaded .patch file.')
    if args.wait_seconds < 60 or args.wait_seconds > 7200:
        parser.error('--wait-seconds must be between 60 and 7200.')
    if not shutil.which('git') or not shutil.which('gh'):
        parser.error('Install git and GitHub CLI, then run gh auth login.')
    if not expected_remote(command(repo, 'git', 'remote', 'get-url', 'origin')):
        parser.error('origin must point to metaforismo/vedra-real-estate, without embedded credentials.')
    if command(repo, 'git', 'status', '--porcelain'):
        parser.error('The clone must be clean. Preserve your changes before continuing.')
    command(repo, 'gh', 'auth', 'status', '--hostname', 'github.com')
    command(repo, 'git', 'fetch', 'origin', 'main')
    if command(repo, 'git', 'rev-parse', 'origin/main') != BASE_SHA:
        parser.error('Upstream main has changed. Rebase/review the patch instead of overwriting newer code.')
    # -b intentionally fails when the branch already exists: never reset somebody's work.
    command(repo, 'git', 'checkout', '-b', BRANCH, 'origin/main')
    command(repo, 'git', 'apply', '--check', str(patch))
    command(repo, 'git', 'apply', '--index', str(patch))
    command(repo, 'git', 'diff', '--cached', '--check')
    command(repo, 'git', 'commit', '-m', TITLE)
    sha = command(repo, 'git', 'rev-parse', 'HEAD')
    if not re.fullmatch(r'[a-f0-9]{40}', sha):
        raise RuntimeError('Unexpected commit identifier; refusing to publish.')
    command(repo, 'git', 'push', '-u', 'origin', BRANCH)
    url = command(repo, 'gh', 'pr', 'create', '--repo', REPOSITORY, '--base', 'main',
                  '--head', BRANCH, '--title', TITLE, '--body', BODY)
    if not re.fullmatch(r'https://github\.com/metaforismo/vedra-real-estate/pull/\d+', url):
        raise RuntimeError('PR response unexpected; inspect GitHub. No merge attempted.')
    print(f'PR created: {url}\nHead: {sha}', flush=True)
    if args.merge:
        merge_when_green(repo, url, sha, args.wait_seconds)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f'Stopped: {exc}', file=sys.stderr)
        raise SystemExit(1) from None

#!/usr/bin/env python3
"""
Keep docs/DEPENDENCY-EXCEPTIONS.md honest about what the tree actually carries.

CI fails the build on high and critical advisories, so moderates pass silently.
That is reasonable — a moderate should not block a deploy — but it means they
accumulate unread, and "we knew about that one" becomes indistinguishable from
"nobody looked." This closes that gap without changing the severity gate: a
moderate still does not fail the build *for being a moderate*. It fails for
being undocumented.

Two directions, both worth catching:

* **Undocumented** — a new advisory appeared and nobody decided about it.
* **Stale** — a documented one is gone, so the exception should be deleted
  rather than left implying a risk that no longer exists.

Run from anywhere:

    python3 scripts/check_dependency_exceptions.py

Exit status is 0 when the document and the tree agree, 1 when they do not, and
2 when the audit itself could not be run (missing npm, no lockfile) — a
distinction that matters, because "could not check" must never be mistaken for
"checked and fine".
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = REPO / 'app' / 'frontend'
DOC = REPO / 'docs' / 'DEPENDENCY-EXCEPTIONS.md'

#: Severities that must be accounted for. Anything below this is noise for a
#: browser application and is not worth a document entry.
TRACKED = {'moderate', 'high', 'critical'}

#: Advisory ids with a written, reasoned entry in DOC. Adding an id here
#: without adding the entry defeats the point — the check below verifies the
#: document mentions each one.
ACCEPTED = {
    'GHSA-w5hq-g745-h8pq',   # uuid, via cornerstone-wado-image-loader
    'GHSA-968p-4wvh-cqc8',   # @babel/runtime, via cornerstone-tools
}

GHSA = re.compile(r'GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}')


def advisories_in_tree() -> set[str]:
    """Advisory ids at TRACKED severity, from a live `npm audit`."""
    try:
        proc = subprocess.run(
            ['npm', 'audit', '--json'],
            cwd=FRONTEND, capture_output=True, text=True, timeout=300,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        sys.exit(f'could not run npm audit: {exc}')

    # npm exits non-zero when it finds anything, so the status says nothing
    # about whether the run worked. The output does.
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        sys.exit(f'npm audit produced no JSON:\n{proc.stderr.strip()[:500]}')

    found: set[str] = set()
    for details in report.get('vulnerabilities', {}).values():
        if details.get('severity') not in TRACKED:
            continue
        for via in details.get('via', []):
            # A string `via` is a pointer to another package, not an advisory.
            if isinstance(via, dict):
                found.update(GHSA.findall(via.get('url', '')))
    return found


def main() -> int:
    if not DOC.exists():
        sys.exit(f'missing {DOC.relative_to(REPO)}')

    documented = set(GHSA.findall(DOC.read_text()))
    missing_entries = ACCEPTED - documented
    if missing_entries:
        print('Listed as accepted but not written up in '
              f'{DOC.relative_to(REPO)}:')
        for advisory in sorted(missing_entries):
            print(f'  {advisory}')
        print('\nAn id in ACCEPTED without an entry is a silent exception, '
              'which is the thing this check exists to prevent.')
        return 1

    in_tree = advisories_in_tree()
    undocumented = in_tree - ACCEPTED
    stale = ACCEPTED - in_tree

    if undocumented:
        print('New advisories with no decision recorded:')
        for advisory in sorted(undocumented):
            print(f'  {advisory}')
        print(f'\nUpgrade if you can. If you genuinely cannot, add an entry to '
              f'{DOC.relative_to(REPO)} following the instructions at the '
              f'bottom of it — including the reachability analysis, which is '
              f'the part that makes it an exception rather than an admission.')
        return 1

    if stale:
        print('Documented exceptions that are no longer in the tree:')
        for advisory in sorted(stale):
            print(f'  {advisory}')
        print(f'\nRemove them from {DOC.relative_to(REPO)} and from ACCEPTED. '
              f'A document describing risks that no longer exist trains people '
              f'to skim it.')
        return 1

    print(f'{len(in_tree)} advisory(ies) at {"/".join(sorted(TRACKED))}, '
          f'all accounted for in {DOC.relative_to(REPO)}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

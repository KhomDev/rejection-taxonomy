#!/usr/bin/env python3
"""Repo hygiene checks: encoding, tripwire tokens, private strings, links.

Three checks, each of which has caught a real problem in this repository or in a
sibling:

1. **Encoding.** Mojibake (a UTF-8 em dash re-saved as cp1252 shows up as
   \u00e2\u20ac\u201d) is invisible in a diff and wrong in every renderer. This fails on
   the byte sequences directly.
2. **Tripwire tokens.** Ecosystem and identity tokens must not appear anywhere
   except where the design allows them. Publishing them would say which
   ecosystems the author works on, which is itself identifying.
3. **Private strings.** A path from the private workspace must never reach a
   public file.

Usage:
    python scripts/check_hygiene.py            # check the whole repo
    python scripts/check_hygiene.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# `scripts/` must be importable whether this file is run as a script or imported
# by the test suite, so that both use the same matcher.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from token_scan import scan_text  # noqa: E402

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "venv", "node_modules"}

# Mojibake byte sequences. These are what a UTF-8 file looks like after a
# round-trip through a cp1252 reader, and they are never intentional.
MOJIBAKE = [
    "\u00e2\u20ac\u201d",  # em dash
    "\u00e2\u20ac\u201c",  # en dash
    "\u00e2\u20ac\u2122",  # right single quote
    "\u00e2\u20ac\u0153",  # left double quote
    "\u00c3\u00a9",        # e-acute
    "\u00c3\u00a8",        # e-grave
    "\u00c2\u00a0",        # nbsp
    "\ufffd",              # replacement character
]

# Private-workspace paths. Never allowed anywhere.
PRIVATE = ["KNOWLEDGE/", "_private-tools", "RESULTS/", "submission_guides/", "PROTOCOLS/", "engagements/"]

# The ONE file that legitimately contains identity tokens: the module whose whole
# job is to declare them. This is not a general allowlist. `tests/test_token_scan.py`
# asserts the set has exactly this one member, and the matcher is boundary-based,
# so an ordinary English word that merely contains a token needs no exemption.
ALLOWED: dict[str, str] = {
    "scripts/token_scan.py": "declares the token vocabulary it scans for",
}



def iter_files() -> list[Path]:
    """Every file that would be committed: tracked plus untracked-but-not-ignored.

    Using git rather than a directory walk is what keeps the private redaction
    blocklist out of the scan. It is gitignored and full of real target names, so
    walking the tree would report the author's own private file as a leak and
    invite an exemption for it. Falls back to a walk when git is unavailable.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        files = [ROOT / line for line in out.splitlines() if line.strip()]
        if files:
            return sorted(files)
    except (OSError, subprocess.CalledProcessError):
        pass
    walked: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        walked.append(path)
    return sorted(walked)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check_encoding(files: list[Path]) -> list[str]:
    problems: list[str] = []
    for path in files:
        name = rel(path)
        # The private blocklist is not distributed and is not our file to
        # re-encode; every other byte in this repository is.
        if name == "redaction-blocklist.PRIVATE.yaml":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as err:
            problems.append(f"{name}: not valid UTF-8 ({err})")
            continue
        for seq in MOJIBAKE:
            if seq in text:
                line = text[: text.index(seq)].count("\n") + 1
                problems.append(
                    f"{rel(path)}:{line}: mojibake {seq!r} - re-save as UTF-8"
                )
    return problems


def check_tripwires(files: list[Path]) -> list[str]:
    problems: list[str] = []
    for path in files:
        name = rel(path)
        if name in ALLOWED:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for token, line in scan_text(text):
            problems.append(
                f"{name}:{line}: tripwire token {token!r} - ecosystem and identity "
                f"tokens are not published here"
            )
    return problems


# Files whose JOB is to name a private path. Kept separate from ALLOWED so that
# a generic "this file is exempt" can never accidentally exempt a private path.
PRIVATE_ALLOWED = {
    "scripts/build_public_export.py": "BANNED_PATTERNS must name what it refuses to emit",
    "scripts/check_hygiene.py": "the checker must name what it searches for",
    "scripts/verify_blocklist.py": "the private blocklist helper names what it searches for",
    "tests/test_hygiene.py": "asserts the checker catches each path",
    "redaction-blocklist.PRIVATE.yaml": "private, gitignored",
}


def check_private(files: list[Path]) -> list[str]:
    problems: list[str] = []
    for path in files:
        name = rel(path)
        if name in PRIVATE_ALLOWED:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for token in PRIVATE:
            if token in text:
                line = text[: text.index(token)].count("\n") + 1
                problems.append(f"{name}:{line}: private path {token!r}")
    return problems


def check_private_blocklist() -> list[str]:
    """Scan every blob in every commit against the private redaction blocklist.

    This is the check that matters most, and the working-tree scan above cannot
    replace it: a token that is deleted in a later commit is still in the history
    forever. It caught a real leak - the classifier had hardcoded the names of
    the firms that audited the author's targets, which narrows the target set.

    Skips when the private blocklist is absent, which is the normal case for
    anyone who is not the author.
    """
    blocklist = ROOT / "redaction-blocklist.PRIVATE.yaml"
    if not blocklist.exists():
        return []
    try:
        import yaml
    except ImportError:
        return ["cannot scan history: PyYAML is not installed"]

    data = yaml.safe_load(blocklist.read_text(encoding="utf-8")) or {}
    # Groups not named as case-sensitive are matched case-insensitively, which
    # is the stricter of the two and therefore fails safe.
    cs_groups = set(data.get("case_sensitive_groups") or [])
    case_sensitive: set[str] = set()
    case_insensitive: set[str] = set()
    for group, values in data.items():
        if group in ("case_sensitive_groups", "case_insensitive_groups"):
            continue
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                token = value.strip()
                if group in cs_groups:
                    case_sensitive.add(token)
                else:
                    case_insensitive.add(token)

    import subprocess

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout

    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for line in git("log", "--all", "--format=%H").split():
        for name in git("ls-tree", "-r", "--name-only", line).splitlines():
            if (line, name) in seen:
                continue
            seen.add((line, name))
            content = git("show", f"{line}:{name}")
            hits = sorted(
                t for t in case_sensitive if re.search(rf"\b{re.escape(t)}\b", content)
            )
            low = content.lower()
            hits += sorted(
                t for t in case_insensitive if re.search(rf"\b{re.escape(t.lower())}\b", low)
            )
            if hits:
                problems.append(
                    f"{line[:8]} {name}: private blocklist token(s) {sorted(set(hits))[:8]}"
                )
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--no-history",
        action="store_true",
        help="skip the git-history scan against the private blocklist",
    )
    args = ap.parse_args(argv)

    files = iter_files()
    encoding = check_encoding(files)
    tripwires = check_tripwires(files)
    private = check_private(files)
    history = [] if args.no_history else check_private_blocklist()

    if args.json:
        print(
            json.dumps(
                {
                    "files_scanned": len(files),
                    "encoding": encoding,
                    "tripwires": tripwires,
                    "private": private,
                    "history": history,
                },
                indent=2,
            )
        )
        return 1 if (encoding or tripwires or private or history) else 0

    total = len(encoding) + len(tripwires) + len(private) + len(history)
    if not total:
        history_note = (
            "" if args.no_history else ", no blocklist token in any commit"
        )
        print(
            f"OK: {len(files)} files - encoding clean, no tripwire tokens, "
            f"no private paths{history_note}"
        )
        return 0

    for label, problems in (
        ("ENCODING", encoding),
        ("TRIPWIRE", tripwires),
        ("PRIVATE", private),
        ("HISTORY", history),
    ):
        for p in problems:
            print(f"{label}  {p}", file=sys.stderr)
    print(f"\n{total} problem(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

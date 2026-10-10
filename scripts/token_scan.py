#!/usr/bin/env python3
"""The identity-token vocabulary, and the one matcher that scans for it.

Both live here so that the check CI runs and the check the test suite runs are
literally the same function: `scripts/check_hygiene.py` imports `scan_text`, and
so does `tests/test_token_scan.py`.

Boundaries
----------
A token counts only when it stands alone as a word. The matcher is the explicit
form of a word boundary:

    (?<![A-Za-z0-9_]) TOKEN (?![A-Za-z0-9_])

That is the fix for a real defect. The previous matcher compared the character
either side of a hit against a set that treated `-`, `_` and `.` as separators,
so a word that merely CONTAINED a token was reported as the token. Widening the
separator set was the wrong repair and exempting the words was worse: the correct
boundary is a word boundary. `tests/test_token_scan.py` pins both directions --
English words that contain a token pass, and every declared token fails.

A token that does not end in a word character (the `erc-` prefix) gets no trailing
boundary, because none can exist there; its leading boundary is what keeps
`commerce-` from matching.
"""

from __future__ import annotations

import re

# A token whose PRESENCE reveals something about the author's targets. Published
# here and nowhere else; `scripts/check_hygiene.py` is the only consumer.
TOKENS: tuple[str, ...] = (
    "sui", "move", "aptos", "ton", "tact", "func", "solana", "anchor",
    "cosmos", "cosmwasm", "ibc", "cairo", "starknet", "near", "polkadot",
    "bounce", "witness", "precompile", "create2", "erc-",
    "hackenproof", "immunefi", "cantina", "sherlock", "code4rena",
)

_WORD_CHAR = re.compile(r"[A-Za-z0-9_]")


def pattern(token: str) -> re.Pattern[str]:
    """The explicit word-boundary pattern for one token."""
    left = r"(?<![A-Za-z0-9_])" if _WORD_CHAR.match(token[0]) else ""
    right = r"(?![A-Za-z0-9_])" if _WORD_CHAR.match(token[-1]) else ""
    return re.compile(left + re.escape(token) + right, re.IGNORECASE)


_COMPILED: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (token, pattern(token)) for token in TOKENS
)


def scan_line(line: str) -> list[str]:
    """Every token that stands alone in one line, in vocabulary order."""
    return [token for token, pat in _COMPILED if pat.search(line)]


def scan_text(text: str) -> list[tuple[str, int]]:
    """(token, 1-based line number) for every token that stands alone."""
    hits: list[tuple[str, int]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for token in scan_line(line):
            hits.append((token, lineno))
    return hits

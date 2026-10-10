#!/usr/bin/env python3
"""Verify the redaction blocklist is COMPLETE against the private source.

DEFENCE IN DEPTH, NOT THE PRIMARY GUARANTEE
-------------------------------------------
The strong guarantee is architectural, and `build_public_export.py --check`
enforces it: every published value must come from a closed vocabulary
(`VALID_TRIAGE`, `VALID_GATES`, `VALID_ROOT_CAUSE`). Source text is never passed
through, so no private token can reach the output *by construction*.

This script exists for the case where that architecture is later changed — a new
free-text column, a widened vocabulary, an `--include-raw` flag someone adds in a
hurry. It derives the token set from the private source itself and reports
anything the blocklist does not cover, so the blocklist stays a real second line
of defence rather than an assumption.

Run it after adding rows to the private database.

Usage:
    python scripts/verify_blocklist.py \
        --source /path/to/private/_REJECTION_DATABASE.md \
        --blocklist redaction-blocklist.PRIVATE.yaml
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required.  pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

# Tokens that appear in the source but are generic English / markdown and must
# not be treated as protocol names. Anything NOT in this list and not in the
# blocklist is reported for review.
GENERIC_ALLOWLIST = {
    # markdown / structure
    "protocol", "report", "rejection", "reason", "triage", "class", "root",
    "cause", "category", "earliest", "catchable", "gate", "harness", "fix",
    "ref", "total", "count", "summary", "statistics", "query", "index", "by",
    "full", "database", "schema", "and", "the", "a", "an", "of", "for", "to",
    "in", "on", "at", "is", "not", "no", "yes", "with", "without", "that",
    "this", "it", "as", "or", "be", "are", "was", "were", "has", "have",
    "had", "but", "if", "then", "than", "so", "such", "from", "into", "over",
    "under", "above", "below", "same", "other", "both", "all", "any", "each",
    "one", "two", "three", "first", "second", "third", "new", "old", "prior",
    "after", "before", "during", "when", "where", "which", "who", "why", "how",
    # triage vocabulary
    "duplicate", "duplicates", "informative", "informational", "invalid",
    "valid", "spam", "held", "applicable", "scope", "design", "issue",
    "intentional", "known", "previously", "reported", "resolved", "accepted",
    "acknowledged", "documented", "privileged", "role", "admin", "owner",
    "input", "validation", "best", "practice", "tradeoff", "visibility",
    "floor", "severity", "payout", "reward", "threshold", "ceiling", "tier",
    "unpaid", "paid", "rewardable", "eligible", "bounty", "program",
    # vuln vocabulary
    "reentrancy", "overflow", "underflow", "oracle", "price", "staleness",
    "stale", "front", "run", "running", "mempool", "race", "griefing", "dos",
    "denial", "service", "freeze", "frozen", "lock", "locked", "fund", "funds",
    "loss", "losses", "theft", "drain", "accounting", "rounding", "precision",
    "dilution", "replay", "signature", "nonce", "reentrant", "callback",
    "storage", "slot", "upgrade", "proxy", "delegate", "multisig", "governance",
    "vault", "pool", "lending", "borrow", "collateral", "liquidation", "staking", "unstaking", "bridge", "swap", "dex", "amm", "clmm", "cdp",
    "stablecoin", "token", "erc20", "erc721", "erc1155", "nft", "defi",
    "wasm",
    # reasoning vocabulary
    "attacker", "attack", "exploit", "exploitable", "unprivileged", "external",
    "internal", "public", "private", "package", "entry", "entrypoint", "caller",
    "recipient", "amount", "balance", "delta", "invariant", "assertion",
    "assert", "panic", "revert", "abort", "state", "config",
    "configuration", "parameter", "bound", "bounds", "check", "guard",
    "missing", "unchecked", "unvalidated", "hardcoded", "fixed", "constant",
    "emission", "accrual", "share", "shares", "fee", "fees", "rate",
    "ratio", "value", "valuation", "supply", "demand", "mint", "burn",
    "transfer", "approve", "allowance", "permit", "deadline", "timestamp",
    "block", "epoch", "clock", "queue", "pending", "claim", "claimable",
    "withdraw", "deposit", "redeem", "repay", # cross-reference / doctrine ids
    "p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11", "p12",
    "p13", "p14", "p15", "p16", "p17", "p18", "p19", "p20", "p21", "p22",
    "s0", "s1", "s2", "s3", "s4", "s5", "inv", "eip", "erc", "cve",
    # generic acronyms and standard assets (not target identifiers)
    "oos", "poc", "usdc", "usdt", "dai", "weth", "eth", "btc", "rpc", "api",
    "ptb", "cei", "tss", "pdf", "bps", "osm", "acl", "mtb", "tvl", "dao",
    "utxo", "fifo", "hop", "kyc", "aml", "crud", "json", "yaml",
    "csv", "sql", "http", "https", "url", "uri", "uuid", "sha", "md5",
    "results", "confirmed", "spot", "coin", "verified", "head", "protocols",
    "interact", "downgraded", "unlogged", "eip170", "erc4626", "aib", "cid", "llm", "ai", "vm", "evm",
    "sdk", "cli", "ci", "cd", "pr", "qa", "ux", "ui", "id", "ids",
    "fn", "tx", "txs", "op", "ops", "msg", "err", "log", "cfg", "env",
    # the author's own handle (appears in the private source, never published)
    "khomdev",
    # common words appearing in the free-text columns
    "realism", "concession", "reachability", "attacker-model", "poc-realism",
    "program-rules", "specificity", "maturity", "snapshot", "post-mortem",
    "headline", "evidence", "mismatch", "self", "harm", "inflicted", "net",
    "positive", "economics", "cooperating", "party", "exit", "prerequisite",
    "combined", "interest", "stuck", "yield", "extraction", "extract",
    "auxiliary", "field", "contradicted", "mechanism", "premise",
    "false", "permanent", "death", "died", "dying", "brick", "bricked",
    "weird", "odd", "strange", "subtle", "obvious", "trivial", "minor",
    "major", "critical", "high", "medium", "low", "info", "insight",
    "unrecoverable", "recoverable", "irreversible", "reversible", "atomic",
    "composite", "finalization", "authority", "indirection", "permission",
    "mask", "emptiness", "accumulator", "terminal", "wrapper", "close",
    "finalize", "enumerate", "lens", "wave", "blind", "quorum", "adjudicator",
}

MIN_TOKEN_LEN = 3


def load_blocklist(path: Path) -> set[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tokens: set[str] = set()
    declaration_keys = {"case_sensitive_groups", "case_insensitive_groups"}
    for group, values in data.items():
        if group in declaration_keys:
            continue
        if isinstance(values, list):
            for v in values:
                if isinstance(v, str) and v.strip():
                    tokens.add(v.strip().lower())
    return tokens


def extract_candidates(source: Path) -> Counter[str]:
    """Every capitalised / protocol-looking token in the private source."""
    text = source.read_text(encoding="utf-8")
    candidates: Counter[str] = Counter()

    # The protocol column of the markdown table.
    in_table = False
    for line in text.splitlines():
        if line.startswith("## Full Database"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            in_table = False
        if not in_table or not line.startswith("|"):
            continue
        if re.match(r"^\|\s*-", line) or re.match(r"^\|\s*(Protocol|Report)\b", line):
            continue
        cols = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if cols:
            candidates[cols[0].strip().lower()] += 1

    # ALL-CAPS tokens anywhere (protocol names are usually uppercase).
    for token in re.findall(r"\b[A-Z][A-Z0-9]{2,}\b", text):
        candidates[token.lower()] += 1

    # Mixed-case product-like tokens (e.g. CamelCase protocol names).
    for token in re.findall(r"\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b", text):
        candidates[token.lower()] += 1

    # Uppercase-prefixed finding IDs, e.g. <PREFIX>-249, <PREFIX>-22.
    for token in re.findall(r"\b[A-Z][A-Z0-9]{3,}-[A-Z]?\d+\b", text):
        candidates[token.lower()] += 1

    return candidates


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--blocklist", type=Path, required=True)
    ap.add_argument(
        "--show-all",
        action="store_true",
        help="list every uncovered token, not just the first 60",
    )
    args = ap.parse_args(argv)

    blocked = load_blocklist(args.blocklist)
    candidates = extract_candidates(args.source)

    print(f"blocklist tokens : {len(blocked)}")
    print(f"source candidates: {len(candidates)}")
    print()

    uncovered: list[tuple[str, int]] = []
    for token, count in candidates.most_common():
        if len(token) < MIN_TOKEN_LEN:
            continue
        if token in blocked or token in GENERIC_ALLOWLIST:
            continue
        # A blocklist entry may be a substring of a longer token (e.g. a base
        # name covers its suffixed variants). Accept any blocked token
        # appearing inside.
        if any(b in token for b in blocked if len(b) >= 4):
            continue
        uncovered.append((token, count))

    if not uncovered:
        print("PASS: every candidate token is covered by the blocklist or allowlist.")
        return 0

    print(f"REVIEW: {len(uncovered)} uncovered token(s) — verify each is not a target name.")
    print()
    limit = len(uncovered) if args.show_all else 60
    for token, count in uncovered[:limit]:
        print(f"  {token:<45} x{count}")
    if len(uncovered) > limit:
        print(f"  ... and {len(uncovered) - limit} more (use --show-all)")
    print()
    print("For each: add it to the blocklist, or add it to GENERIC_ALLOWLIST if generic.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

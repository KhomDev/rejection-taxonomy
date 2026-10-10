#!/usr/bin/env python3
"""Compute every published aggregate from data/rejections.csv.

Nothing in the README is hand-written arithmetic. The tables between
`<!-- BEGIN:generated -->` and `<!-- END:generated -->` are produced by this
script, and `--check` fails if the README has drifted from the data.

Usage:
    python scripts/stats.py              # rewrite data/summary.json and the README block
    python scripts/stats.py --check      # exit 1 if either would change
    python scripts/stats.py --json       # print the aggregate object and exit
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_PATH = DATA / "rejections.csv"
SUMMARY_PATH = DATA / "summary.json"
README = ROOT / "README.md"

BEGIN = "<!-- BEGIN:generated -->"
END = "<!-- END:generated -->"

WITHHELD = "withheld"

#: Triage classes that count as "the analysis did not hold up".
#:
#: STRICT: the impact itself was fabricated. One row.
#: BROAD:  that, plus "no security impact / no attacker profit" and
#:         "intentional design / not a bug" - in both, the researcher was
#:         wrong about the behaviour being a vulnerability.
#:
#: The earlier published claim used the informational bucket alone (16/97) as
#: the numerator and called the remaining 84% "targeting". That is not a
#: definition of anything: it is 100% minus one bucket, and it counts
#: intentional-design rows as targeting failures when they are analysis
#: failures. Both definitions are published with their counts.
#: The gates runnable before reading target code. D1 is runnable pre-hunt, but
#: only against a public record - the program's known issues and its published
#: audits - not against the finding's own prose.
PREHUNT_GATES = {
    "D1_duplicate_check",
    "G1_severity_floor",
    "G2_exclusion_clause",
    "G3_scope_tree",
    "G4_prior_audit",
    "G5_test_intent",
}

STRICT_ANALYSIS = {"spam"}
BROAD_ANALYSIS = {"spam", "informational", "intentional_design"}


def rows() -> list[dict]:
    with CSV_PATH.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def pct(n: int, total: int) -> str:
    return f"{100.0 * n / total:.1f}%"


def compute(data: list[dict]) -> dict:
    total = len(data)
    triage = Counter(r["triage_class"] for r in data)
    gate = Counter(r["earliest_gate"] for r in data)
    family = Counter(r["bug_family"] for r in data)
    mechanism = Counter(r["mechanism_class"] for r in data)
    dup_source = Counter(r["duplicate_source"] for r in data)
    preventable = Counter(r["preventable_by"] for r in data)

    published = [r for r in data if r["family_id"] != WITHHELD]
    families = {r["family_id"] for r in published}
    repeats = [r for r in data if r["repeat_of_own"] == "true"]

    # A "family" with more than one published row is a repeated submission.
    fam_sizes = Counter(r["family_id"] for r in published)
    repeated_families = {f: n for f, n in fam_sizes.items() if n > 1}

    strict = sum(triage.get(k, 0) for k in STRICT_ANALYSIS)
    broad = sum(triage.get(k, 0) for k in BROAD_ANALYSIS)

    prehunt = sum(n for g, n in gate.items() if g in PREHUNT_GATES)

    return {
        "total": total,
        "prehunt_catchable": prehunt,
        "prehunt_catchable_pct": round(100.0 * prehunt / total, 1),
        "withheld_rows": sum(1 for r in data if r["family_id"] == WITHHELD),
        "effective_n": len(families),
        "repeat_rows": len(repeats),
        "repeated_families": len(repeated_families),
        "largest_family": max(fam_sizes.values()) if fam_sizes else 0,
        "triage": dict(triage.most_common()),
        "gate": dict(gate.most_common()),
        "bug_family": dict(family.most_common()),
        "mechanism_class": dict(mechanism.most_common()),
        "duplicate_source": dict(dup_source.most_common()),
        "preventable_by": dict(preventable.most_common()),
        "analysis_split": {
            "strict": strict,
            "strict_pct": round(100.0 * strict / total, 1),
            "broad": broad,
            "broad_pct": round(100.0 * broad / total, 1),
            "old_numerator_pct": round(100.0 * triage.get("informational", 0) / total, 1),
            "old_remainder_pct": round(
                100.0 * (total - triage.get("informational", 0)) / total, 1
            ),
        },
    }


def render(agg: dict) -> str:
    total = agg["total"]
    out: list[str] = []
    a = out.append

    a("### Headline numbers")
    a("")
    a("| Triage outcome | Count | Share |")
    a("|---|---:|---:|")
    labels = {
        "duplicate": "Duplicate / previously reported",
        "out_of_scope": "Out of scope - boundary or exclusion clause",
        "informational": "Informational - no security impact / no attacker profit",
        "intentional_design": "Intentional design / not a bug",
        "below_payout_floor": "Valid, but below the payout floor",
        "spam": "SPAM - fabricated impact contradicted by the PoC",
    }
    for key, n in agg["triage"].items():
        a(f"| {labels.get(key, key)} | {n} | {pct(n, total)} |")
    a(f"| **Total** | **{total}** | **100%** |")
    a("")
    a(
        f"**Effective n: {agg['effective_n']} distinct bug families.** {total} rows are not "
        f"{total} independent observations. {agg['repeat_rows']} rows sit in "
        f"{agg['repeated_families']} families that were submitted more than once "
        f"(the largest family has {agg['largest_family']} rows). A family whose first "
        f"submission predates this log cannot be detected at all, so this is a lower "
        f"bound on self-duplication."
    )
    a("")
    a("### Where they died")
    a("")
    a("| Earliest gate | Count | Share |")
    a("|---|---:|---:|")
    for key, n in agg["gate"].items():
        a(f"| `{key}` | {n} | {pct(n, total)} |")
    a("")
    a("### What kind of bug each row was")
    a("")
    a("| `mechanism_class` | Count |")
    a("|---|---:|")
    for key, n in agg["mechanism_class"].items():
        a(f"| `{key}` | {n} |")
    a("")
    a("### Where the duplicate signal lived")
    a("")
    a("| `duplicate_source` | Count |")
    a("|---|---:|")
    for key, n in agg["duplicate_source"].items():
        a(f"| `{key}` | {n} |")
    a("")
    a("### What could have prevented each rejection")
    a("")
    a("| `preventable_by` | Count | Share |")
    a("|---|---:|---:|")
    for key, n in agg["preventable_by"].items():
        a(f"| `{key}` | {n} | {pct(n, total)} |")
    a("")
    a("### Did the analysis hold up?")
    a("")
    s = agg["analysis_split"]
    a("| Definition | Numerator | Count | Share |")
    a("|---|---|---:|---:|")
    a(
        f"| **strict** - the impact was fabricated | `spam` | {s['strict']} | "
        f"{s['strict_pct']}% |"
    )
    a(
        f"| **broad** - no impact, intentional design, or fabricated | "
        f"`spam` + `informational` + `intentional_design` | {s['broad']} | "
        f"{s['broad_pct']}% |"
    )
    a("")
    a(
        f"An earlier version of this document used `informational` alone "
        f"({s['old_numerator_pct']}%) as the numerator and called the remaining "
        f"{s['old_remainder_pct']}% 'targeting'. That is not a definition: it is 100% "
        f"minus one bucket, and it counts intentional-design rows as targeting failures "
        f"when they are analysis failures. Both honest definitions are above."
    )
    return "\n".join(out)


def apply_readme(block: str, check: bool) -> bool:
    """Rewrite the generated block. Return True if the file changed (or would)."""
    text = README.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        print(f"ERROR: {README} has no {BEGIN} / {END} markers", file=sys.stderr)
        raise SystemExit(2)
    pattern = re.compile(
        re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL
    )
    replacement = f"{BEGIN}\n\n{block}\n\n{END}"
    updated = pattern.sub(lambda _: replacement, text, count=1)
    if updated == text:
        return False
    if not check:
        README.write_text(updated, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if anything is stale")
    ap.add_argument("--json", action="store_true", help="print aggregates and exit")
    args = ap.parse_args(argv)

    data = rows()
    agg = compute(data)

    if args.json:
        print(json.dumps(agg, indent=2))
        return 0

    # newline="\\n": Windows text mode would otherwise emit CRLF and fight
    # .gitattributes on every clone.
    # Compare BYTES, not text. read_text applies universal-newline translation,
    # so a CRLF file and an LF string compare equal and a line-ending drift would
    # never be detected or fixed.
    summary_text = json.dumps(agg, indent=2) + "\n"
    old_bytes = SUMMARY_PATH.read_bytes() if SUMMARY_PATH.exists() else b""
    summary_stale = old_bytes != summary_text.encode("utf-8")

    block = render(agg)
    readme_stale = apply_readme(block, check=True)

    if args.check:
        if summary_stale:
            print("STALE: data/summary.json does not match the data", file=sys.stderr)
        if readme_stale:
            print("STALE: README generated block does not match the data", file=sys.stderr)
        if summary_stale or readme_stale:
            return 1
        print(f"OK: summary.json and README are current ({len(data)} rows)")
        return 0

    if summary_stale:
        SUMMARY_PATH.write_text(summary_text, encoding="utf-8", newline="\n")
    apply_readme(block, check=False)
    print(f"wrote data/summary.json and the README generated block ({len(data)} rows)")
    print(f"  effective n: {agg['effective_n']}")
    print(f"  analysis split: strict {agg['analysis_split']['strict']} / broad {agg['analysis_split']['broad']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

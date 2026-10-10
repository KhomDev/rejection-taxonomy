#!/usr/bin/env python3
"""Query the rejection dataset.

Answers the questions the dataset exists to answer, without making you remember
jq syntax.

Usage:
    python scripts/query.py                              # overview + distributions
    python scripts/query.py --triage duplicate           # one triage outcome
    python scripts/query.py --gate G1_severity_floor     # one gate
    python scripts/query.py --family oracle              # one bug family
    python scripts/query.py --mechanism-class replay_scope
    python scripts/query.py --duplicate-source own_prior
    python scripts/query.py --preventable-by public_record
    python scripts/query.py --repeats                    # rows repeating an earlier family
    python scripts/query.py --root-cause no_attacker_win
    python scripts/query.py --prehunt                    # the pre-hunt split
    python scripts/query.py --triage duplicate --json

Filters combine with AND. `--json` emits the matching rows for piping.

There is no `--paid-only` and no `paid` column: every row in this dataset was
rejected. The dataset has no positive class.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# The gates runnable before reading any target code. D1 is runnable pre-hunt, but
# only against a public record - the program's known issues and its published
# audits - not against the finding's own prose.
PREHUNT_GATES = {
    "D1_duplicate_check",
    "G1_severity_floor",
    "G2_exclusion_clause",
    "G3_scope_tree",
    "G4_prior_audit",
    "G5_test_intent",
}

GATE_MEANING = {
    "D1_duplicate_check": "duplicate / known-family check (public record only)",
    "G1_severity_floor": "is there a payout tier at this severity?",
    "G2_exclusion_clause": "does an exclusion clause cover this?",
    "G3_scope_tree": "is the root cause inside the scoped files?",
    "G4_prior_audit": "is this surface already closed?",
    "G5_test_intent": "does the project's test suite assert this is intended?",
    "design_review": "intentional design / no impact review",
    "program_ceiling": "program-level severity ceiling",
    "P7_best_practice": "best-practice critique",
    "P12_no_persisted_impact": "revert-only, no persisted impact",
    "P16_below_floor": "confirmed mechanics, below the severity floor",
    "P17_no_attacker_win": "no attacker-win / self-harm / no net-positive economics",
    "P18_design_tradeoff": "design tradeoff",
    "P19_headline_mismatch": "headline contradicted by PoC evidence",
    "P20_cooperating_party": "requires a cooperating party",
    "REALISM": "realism gates (attacker-model, config, concession)",
    "UNCLASSIFIED": "no gate token recognised",
}


def load() -> list[dict]:
    path = DATA / "rejections.csv"
    if not path.exists():
        print(f"ERROR: {path} not found. Run scripts/build_public_export.py first.", file=sys.stderr)
        raise SystemExit(2)
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def bar(n: int, total: int, width: int = 28) -> str:
    filled = round(width * n / total) if total else 0
    return "#" * filled + "." * (width - filled)


def show_distribution(title: str, counts: Counter, total: int) -> None:
    print(f"\n{title}")
    for name, n in counts.most_common():
        print(f"  {name:<26} {n:>3}  {n / total:>5.1%}  {bar(n, total)}")


def overview(rows: list[dict]) -> None:
    total = len(rows)
    print(f"rejection-taxonomy - {total} logged rejections\n")
    show_distribution("By triage outcome", Counter(r["triage_class"] for r in rows), total)
    show_distribution("By bug family", Counter(r["bug_family"] for r in rows), total)
    show_distribution(
        "By mechanism class", Counter(r["mechanism_class"] for r in rows), total
    )

    gates = Counter(r["earliest_gate"] for r in rows)
    print("\nBy earliest catchable gate")
    for name, n in gates.most_common():
        mark = "*" if name in PREHUNT_GATES else " "
        print(f" {mark}{name:<26} {n:>3}  {n / total:>5.1%}  {GATE_MEANING.get(name, '')}")

    catchable = sum(n for g, n in gates.items() if g in PREHUNT_GATES)
    print("\n  * = runnable before reading any code")
    print(f"  pre-hunt catchable: {catchable}/{total} ({catchable / total:.1%})")
    print(f"  needed the finding in hand: {total - catchable}/{total} ({(total - catchable) / total:.1%})")

    published = [r for r in rows if r["family_id"] != "withheld"]
    print(f"\n  effective n: {len({r['family_id'] for r in published})} distinct bug families")
    print(f"  rows repeating an earlier family: {sum(1 for r in rows if r['repeat_of_own'] == 'true')}")


def show_rows(rows: list[dict], verbose: bool) -> None:
    if not rows:
        print("\nno rows match.")
        return
    print(f"\n{len(rows)} row(s):\n")
    for r in rows:
        print(f"  {r['id']}  [{r['bug_family']}]  {r['triage_class']} via {r['earliest_gate']}")
        if verbose:
            print(
                f"      family={r['family_id']} mechanism={r['mechanism_class']} "
                f"repeat_of_own={r['repeat_of_own']}"
            )
            print(
                f"      duplicate_source={r['duplicate_source']} "
                f"preventable_by={r['preventable_by']} root_cause={r['root_cause_class']}"
            )
        else:
            print(
                f"      {r['mechanism_class']} | dup={r['duplicate_source']} | "
                f"preventable={r['preventable_by']}"
            )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--triage", help="filter by triage_class")
    ap.add_argument("--gate", help="filter by earliest_gate")
    ap.add_argument("--family", help="filter by bug_family")
    ap.add_argument("--mechanism-class", dest="mechanism_class", help="filter by mechanism_class")
    ap.add_argument("--duplicate-source", dest="duplicate_source", help="filter by duplicate_source")
    ap.add_argument("--preventable-by", dest="preventable_by", help="filter by preventable_by")
    ap.add_argument("--root-cause", dest="root_cause", help="filter by root_cause_class")
    ap.add_argument("--repeats", action="store_true", help="only rows repeating an earlier family")
    ap.add_argument("--prehunt", action="store_true", help="only rows catchable by a pre-hunt gate")
    ap.add_argument("--posthunt", action="store_true", help="only rows that needed the finding in hand")
    ap.add_argument("--json", action="store_true", help="emit matching rows as JSON")
    ap.add_argument("-v", "--verbose", action="store_true", help="show the full row")
    args = ap.parse_args(argv)

    rows = load()

    if not any(
        [
            args.triage,
            args.gate,
            args.family,
            args.mechanism_class,
            args.duplicate_source,
            args.preventable_by,
            args.root_cause,
            args.repeats,
            args.prehunt,
            args.posthunt,
        ]
    ):
        overview(rows)
        print(
            "\nFilter with --triage, --gate, --family, --mechanism-class, "
            "--duplicate-source, --preventable-by, --root-cause, --repeats, --prehunt."
        )
        return 0

    out = rows
    if args.triage:
        out = [r for r in out if r["triage_class"] == args.triage]
    if args.gate:
        out = [r for r in out if r["earliest_gate"] == args.gate]
    if args.family:
        out = [r for r in out if r["bug_family"] == args.family]
    if args.mechanism_class:
        out = [r for r in out if r["mechanism_class"] == args.mechanism_class]
    if args.duplicate_source:
        out = [r for r in out if r["duplicate_source"] == args.duplicate_source]
    if args.preventable_by:
        out = [r for r in out if r["preventable_by"] == args.preventable_by]
    if args.root_cause:
        out = [r for r in out if r["root_cause_class"] == args.root_cause]
    if args.repeats:
        out = [r for r in out if r["repeat_of_own"] == "true"]
    if args.prehunt:
        out = [r for r in out if r["earliest_gate"] in PREHUNT_GATES]
    if args.posthunt:
        out = [r for r in out if r["earliest_gate"] not in PREHUNT_GATES]

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    show_rows(out, args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

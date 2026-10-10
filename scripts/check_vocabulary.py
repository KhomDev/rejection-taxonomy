#!/usr/bin/env python3
"""Check this repository's vocabulary against a pinned copy of the sibling repos.

The three repositories share one vocabulary. P2 means "privileged-role-gated"
in viability-gate and used to mean "duplicate check" here, which is exactly the
class of bug this checker exists to prevent: an id that means two things.

What is pinned, and where:

  rejection-taxonomy  owns  earliest_gate, triage_class, root_cause_class,
                            bug_family, mechanism_class, duplicate_source,
                            preventable_by
  bounty-economics    owns  tier_shape, exclusion class, floor_status
  viability-gate      owns  anti-pattern ids (P1..P22), gate ids (G1..G7, D1)

The gate ids are SHARED between rejection-taxonomy (as earliest_gate) and
viability-gate (as gate ids). This checker asserts they agree.

It reads the sibling repositories when they are present on disk and SKIPS
cleanly when they are not, so it does not fail a standalone clone or CI.

Usage:
    python scripts/check_vocabulary.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIBLINGS = ROOT.parent

# Gate ids this repository publishes as earliest_gate that are also real gate
# ids in viability-gate. D1 is the shared one that used to collide.
SHARED_GATE_IDS = {
    "D1_duplicate_check": "D1",
    "G1_severity_floor": "G1",
    "G2_exclusion_clause": "G2",
    "G3_scope_tree": "G3",
    "G4_prior_audit": "G4",
    "G5_test_intent": "G5",
}


def published_gate_ids() -> set[str]:
    path = ROOT / "data" / "rejections.csv"
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {r["earliest_gate"] for r in rows}


def viability_gate_ids() -> set[str] | None:
    gates = SIBLINGS / "viability-gate" / "rules" / "gates.yaml"
    if not gates.exists():
        return None
    text = gates.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*- id:\s*(\S+)", text, re.MULTILINE))


def main() -> int:
    gates = viability_gate_ids()
    if gates is None:
        print("SKIP: the sibling viability-gate repository is not present")
        return 0

    ours = published_gate_ids()
    problems = []
    for published, gate_id in SHARED_GATE_IDS.items():
        if published in ours and gate_id not in gates:
            problems.append(
                f"{published} is published here but gate id {gate_id} does not exist "
                f"in viability-gate/rules/gates.yaml"
            )
    for gid in sorted(ours & set(SHARED_GATE_IDS)):
        want = SHARED_GATE_IDS[gid]
        if want not in gates:
            problems.append(f"gate id {want} (for {gid}) is missing from the sibling")
    # The rename must hold: nothing may still publish the old id.
    if "P2_duplicate_check" in ours:
        problems.append(
            "P2_duplicate_check is still published; it was renamed to "
            "D1_duplicate_check because P2 means privileged-role-gated in "
            "viability-gate"
        )

    if problems:
        for p in problems:
            print(f"VOCAB  {p}", file=sys.stderr)
        return 1
    print(
        f"OK: {len(SHARED_GATE_IDS)} shared gate id(s) agree with "
        f"viability-gate ({', '.join(sorted(gates))})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

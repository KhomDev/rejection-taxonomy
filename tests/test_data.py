#!/usr/bin/env python3
"""Tests for the published dataset.

Run:
    python -m pytest tests/ -q
    python tests/test_data.py          # no pytest required

These assert the things that would otherwise drift silently: totals that disagree
with the summary, a row that left the allowlist, a column that grew a target
dimension or a free-text field, a withheld row that leaked a field, and README
tables that no longer match the data they claim to quote.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CSV_PATH = DATA / "rejections.csv"
JSON_PATH = DATA / "rejections.json"
SUMMARY_PATH = DATA / "summary.json"
README = ROOT / "README.md"

sys.path.insert(0, str(ROOT / "scripts"))

from build_public_export import (  # noqa: E402
    ALLOWED,
    COLUMNS,
    WITHHELD,
    WITHHELD_MECHANISM,
    WITHHELD_TRIAGE,
)

# The six gates runnable before reading target code.
PREHUNT_GATES = {
    "D1_duplicate_check",
    "G1_severity_floor",
    "G2_exclusion_clause",
    "G3_scope_tree",
    "G4_prior_audit",
    "G5_test_intent",
}

# Columns that must never appear: the target dimension, and free text.
FORBIDDEN_COLUMNS = {
    "protocol",
    "protocol_class",
    "chain",
    "ecosystem",
    "language",
    "severity",
    "severity_claimed",
    "severity_assigned",
    "date",
    "submission_date",
    "module",
    "function",
    "line",
    "protocol_name",
    "mechanism",
    "paid",
    "report_title",
    "rejection_reason",
}


def rows() -> list[dict]:
    with CSV_PATH.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- existence


def test_data_files_exist():
    for p in (CSV_PATH, JSON_PATH, SUMMARY_PATH):
        assert p.exists(), f"missing {p}"


def test_row_count_is_111():
    assert len(rows()) == 111, f"expected 111 rows, got {len(rows())}"


def test_json_matches_csv():
    csv_rows = rows()
    json_rows = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    assert len(csv_rows) == len(json_rows), "csv and json disagree on row count"
    for c, j in zip(csv_rows, json_rows, strict=False):
        assert c["id"] == j["id"], f"row order diverged at {c['id']}"
        assert c["mechanism_class"] == j["mechanism_class"], f"diverged at {c['id']}"
    # JSON types the boolean field; the CSV carries the string form.
    for c, j in zip(csv_rows, json_rows, strict=False):
        if c["repeat_of_own"] in {"true", "false"}:
            assert isinstance(j["repeat_of_own"], bool), c["id"]


# ---------------------------------------------------------------- schema


def test_no_target_dimension_and_no_free_text():
    cols = set(rows()[0].keys())
    leaked = cols & FORBIDDEN_COLUMNS
    assert not leaked, f"schema exposes forbidden columns: {sorted(leaked)}"


def test_expected_columns_exactly():
    assert list(rows()[0].keys()) == list(COLUMNS), "columns changed"


def test_every_value_is_in_its_allowlist():
    # This is the whole design: a value outside the vocabulary is a build
    # failure. A denylist could not have made this assertion.
    for row in rows():
        for column, allowed in ALLOWED.items():
            assert row[column] in allowed, (
                f"{row['id']}: {column}={row[column]!r} is outside the vocabulary"
            )


def test_family_ids_are_opaque_and_sequential():
    ids = [r["family_id"] for r in rows() if r["family_id"] != WITHHELD]
    for fid in ids:
        assert re.match(r"^F-\d{3}$", fid), f"bad family id {fid!r}"
    # Families are assigned in first-seen order, so the first row always opens
    # a new family and the sequence is dense.
    assert ids[0] == "F-001"
    numeric = sorted(int(f[2:]) for f in set(ids))
    assert numeric == list(range(1, len(numeric) + 1)), "family ids are not dense"


# ---------------------------------------------------------------- withholding


def test_below_payout_floor_rows_ship_only_the_allowed_fields():
    withheld = [r for r in rows() if r["triage_class"] == WITHHELD_TRIAGE]
    assert withheld, "expected the below_payout_floor rows to exist"
    for r in withheld:
        assert r["mechanism_class"] == WITHHELD_MECHANISM, r["id"]
        for field in ("family_id", "repeat_of_own", "duplicate_source", "preventable_by"):
            assert r[field] == WITHHELD, f"{r['id']} leaks {field}={r[field]!r}"


def test_no_withheld_row_contributes_to_an_effective_n():
    published = {r["family_id"] for r in rows() if r["family_id"] != WITHHELD}
    assert WITHHELD not in published
    assert summary()["effective_n"] == len(published)


# ---------------------------------------------------------------- totals


def test_triage_totals_match_summary():
    from collections import Counter

    actual = Counter(r["triage_class"] for r in rows())
    assert dict(actual) == summary()["triage"], "triage totals drifted"


def test_gate_totals_match_summary():
    from collections import Counter

    actual = Counter(r["earliest_gate"] for r in rows())
    assert dict(actual) == summary()["gate"], "gate totals drifted"


def test_duplicate_source_totals_match_summary():
    from collections import Counter

    actual = Counter(r["duplicate_source"] for r in rows())
    assert dict(actual) == summary()["duplicate_source"]


def test_preventable_by_totals_match_summary():
    from collections import Counter

    actual = Counter(r["preventable_by"] for r in rows())
    assert dict(actual) == summary()["preventable_by"]


def test_prehunt_figure_is_correct():
    s = summary()
    catchable = sum(1 for r in rows() if r["earliest_gate"] in PREHUNT_GATES)
    assert catchable == s["prehunt_catchable"] == 78, catchable
    assert abs(s["prehunt_catchable_pct"] - 70.3) < 0.05


def test_effective_n_and_repeats_are_reported():
    s = summary()
    published = [r for r in rows() if r["family_id"] != WITHHELD]
    assert s["effective_n"] == len({r["family_id"] for r in published})
    repeats = sum(1 for r in rows() if r["repeat_of_own"] == "true")
    assert s["repeat_rows"] == repeats
    # The original article claimed two rows were self-repeats; the real count is
    # higher, and it must stay visible.
    assert repeats >= 7, f"expected at least 7 repeat rows, got {repeats}"


def test_analysis_split_is_both_definitions():
    s = summary()["analysis_split"]
    assert s["strict"] == 1, s
    assert s["broad"] == 39, s
    assert abs(s["broad_pct"] - 35.1) < 0.05
    # The old framing published informational-alone and called the remainder "targeting".
    assert abs(s["old_numerator_pct"] - 19.8) < 0.05


def test_duplicate_gate_counts_are_reconciled():
    # 43 rows are duplicates by triage outcome; 41 record D1_duplicate_check as
    # the earliest catchable gate. Both are published, with their definitions.
    s = summary()
    assert s["triage"]["duplicate"] == 43
    assert s["gate"]["D1_duplicate_check"] == 41


# ---------------------------------------------------------------- README


def test_readme_csv_examples_match_the_data():
    """Every CSV row quoted in the README must match the real data."""
    by_id = {r["id"]: r for r in rows()}
    text = README.read_text(encoding="utf-8")
    checked = 0
    for line in text.splitlines():
        if not re.match(r"^R-\d{3},", line.strip()):
            continue
        parsed = next(csv.reader([line.strip()]))
        if len(parsed) != len(COLUMNS):
            continue
        by_id_parsed = dict(zip(COLUMNS, parsed, strict=False))
        rid = by_id_parsed["id"]
        assert rid in by_id, f"README quotes {rid}, which is not in the dataset"
        real = by_id[rid]
        for column in COLUMNS:
            assert by_id_parsed[column] == real[column], f"{rid}: {column} differs"
        checked += 1
    assert checked >= 1, f"expected the README to quote at least 1 row, found {checked}"


def test_schema_doc_numbers_match_the_summary():
    """data/SCHEMA.md is prose, but its tables carry counts. Fail if they drift.

    The two tables share value names (both have an `unknown` row), so each is
    sliced out by its heading before matching.
    """
    s = summary()
    text = (DATA / "SCHEMA.md").read_text(encoding="utf-8")

    def section(heading: str, stop: str) -> str:
        start = text.index(heading)
        end = text.index(stop, start)
        return text[start:end]

    dup = section("### duplicate_source", "### preventable_by")
    prev = section("### preventable_by", "### root_cause_class")

    for value, count in s["duplicate_source"].items():
        row = re.search(rf"^\| `?{re.escape(value)}`? \|[^|]*\| (\d+) \|$", dup, re.M)
        assert row, f"SCHEMA.md has no row for duplicate_source {value}"
        assert int(row.group(1)) == count, (
            f"SCHEMA.md says duplicate_source {value}={row.group(1)}, data says {count}"
        )
    for value, count in s["preventable_by"].items():
        row = re.search(rf"^\| `?{re.escape(value)}`? \|[^|]*\| (\d+) \|", prev, re.M)
        assert row, f"SCHEMA.md has no row for preventable_by {value}"
        assert int(row.group(1)) == count, (
            f"SCHEMA.md says preventable_by {value}={row.group(1)}, data says {count}"
        )


def test_documented_vocabulary_sizes_match_the_code():
    """The README and SCHEMA.md state vocabulary sizes in prose.

    Prose about a closed vocabulary drifts the moment a class is added, and a
    wrong count in the section that argues "everything here is checkable" is
    worse than no count. These assertions are the guard.
    """
    from build_public_export import (
        BUG_FAMILIES,
        MECHANISM_RULES,
        VALID_GATES,
        VALID_MECHANISM,
        VALID_ROOT_CAUSE,
        VALID_TRIAGE,
    )

    assert len(BUG_FAMILIES) == 19
    assert len(MECHANISM_RULES) == 32
    assert len(VALID_MECHANISM) == 34  # 32 classes + other_mechanism + withheld_valid
    assert len(VALID_TRIAGE) == 6
    assert len(VALID_ROOT_CAUSE) == 20
    # 16 gate values plus the UNCLASSIFIED sentinel.
    assert len(VALID_GATES) == 17

    readme = README.read_text(encoding="utf-8")
    schema = (DATA / "SCHEMA.md").read_text(encoding="utf-8")
    assert "19 families" in readme
    assert "32 classes, plus 2 sentinels" in readme
    assert "16 gates, plus the" in readme
    assert "20 reasons" in readme
    assert "6 outcomes" in readme
    assert "34 members" in schema
    assert "17 members" in schema

    # And the counts the prose gives for what is ACTUALLY USED must match.
    used_mech = len({r["mechanism_class"] for r in rows()})
    used_gate = len({r["earliest_gate"] for r in rows()})
    assert used_mech == 33, used_mech
    assert used_gate == 13, used_gate
    assert "33 are used" in schema
    assert "13 are" in schema and "used" in schema


def test_readme_generated_block_is_current():
    """The README tables are generated. Fail if they have drifted."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "stats.py"), "--check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, (
        "README / summary.json are stale - run scripts/stats.py\n"
        + result.stdout
        + result.stderr
    )


def test_readme_states_the_dataset_has_no_positive_class():
    text = README.read_text(encoding="utf-8").lower()
    assert "no positive class" in text, "the README must state the missing positive class"


def test_readme_does_not_claim_a_wrong_row_count():
    text = README.read_text(encoding="utf-8")
    assert "111" in text, "README does not state the row count"
    assert "121" not in text, "README still mentions the old 121 count"


def test_readme_no_longer_claims_a_preventability_figure_without_definitions():
    text = README.read_text(encoding="utf-8")
    # The old claim is gone; the difference is documented instead.
    assert "preventable by pre-hunt gates alone" not in text
    assert "no positive class" in text.lower()


# ---------------------------------------------------------------- runner


def main() -> int:
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ok    {name}")
        except AssertionError as err:
            failed += 1
            print(f"  FAIL  {name}: {err}")
        except Exception as err:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {name}: {type(err).__name__}: {err}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Derive the public rejection corpus from the private RESULTS database.

NEVER hand-edit data/rejections.csv or data/rejections.json. Run this script.

DESIGN PRINCIPLE
----------------
The public dataset carries NO target dimension and NO free text. Not the
protocol, not the chain, not the ecosystem, not the date, not the severity, and
not an authored sentence about the bug. What it publishes is the *categorical
shape* of a rejection:

    (bug family, mechanism class, triage outcome, earliest catchable gate,
     root cause class, whether it repeats an earlier family, where the
     duplicate signal lived, and what could have prevented it)

Every published value comes from a closed vocabulary defined in this file and
documented in data/SCHEMA.md. Validation is by ALLOWLIST, not denylist, so a
paraphrase cannot slip through: a value that is not in the vocabulary is a build
failure, not a warning.

An earlier revision published a free-text `mechanism` column and validated it
against a denylist. That is the hole this design closes. An earlier draft also
published `chain` and `ecosystem`; those columns are gone and `--check` fails
if they come back.

The private database and this script stay private. The tool is the public good;
the data is not.

Usage:
    python scripts/build_public_export.py \
        --source /path/to/private/_REJECTION_DATABASE.md \
        --blocklist /path/to/private/redaction-blocklist.yaml \
        --out data/

    # verify an existing export without the private inputs
    python scripts/build_public_export.py --check --out data/
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# The aggregate definitions live in ONE place. Both this script and stats.py
# import them, so the two writers of data/summary.json cannot disagree about
# what an aggregate is.
from stats import compute

# --------------------------------------------------------------------------
# Public row schema.
#
# Ten columns. Nine are closed-vocabulary categories; one (`id`) is an ordinal.
# There is deliberately no field that could carry free text, and no field that
# could identify a target.
# --------------------------------------------------------------------------

COLUMNS: tuple[str, ...] = (
    "id",
    "family_id",
    "bug_family",
    "mechanism_class",
    "triage_class",
    "earliest_gate",
    "root_cause_class",
    "repeat_of_own",
    "duplicate_source",
    "preventable_by",
)

#: Sentinel for a row whose descriptive payload is withheld entirely. Rows the
#: program could not pay for are confirmed-valid bugs; a mechanism class plus a
#: family id would say more about them than a rejection should. See SCHEMA.md.
WITHHELD = "withheld"

#: Rows with this triage class ship ONLY bug_family, triage_class, earliest_gate,
#: root_cause_class and mechanism_class=withheld_valid. Everything else is
#: replaced by WITHHELD.
WITHHELD_TRIAGE = "below_payout_floor"
WITHHELD_MECHANISM = "withheld_valid"


@dataclass
class PublicRow:
    id: str
    family_id: str
    bug_family: str
    mechanism_class: str
    triage_class: str
    earliest_gate: str
    root_cause_class: str
    repeat_of_own: str
    duplicate_source: str
    preventable_by: str


# --------------------------------------------------------------------------
# Triage bucketing.
#
# Mirrors the private workspace's canonical `scripts/rejection-db-stats.py`
# EXACTLY in outcome, including bucket order, so published totals cannot drift
# from the source of truth. First matching rule wins.
#
# Keys are REGEXES, not literals. The canonical script matches one private
# program-framework name as a literal string; that name must not appear in a
# published file, so the equivalent is expressed generically here. The generic
# form matches the same rows and no others - verified by the totals.
# --------------------------------------------------------------------------

BUCKETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "below_payout_floor",
        (
            r"not paid",
            r"below payout",
            r"payout-floor",
            # Generic form of the canonical script's literal framework name:
            # a valid finding recorded as unpaid because the program pays only
            # above a given severity. Matches "<any> payout" in a scope phrase.
            r"out of scope for \S+ payout",
        ),
    ),
    ("spam", (r"spam",)),
    ("duplicate", (r"duplicate",)),
    ("out_of_scope", (r"out of scope", r"oos")),
    ("informational", (r"inform",)),
    ("intentional_design", ()),  # fallback, mirrors the canonical script
)

VALID_TRIAGE = {label for label, _ in BUCKETS}


def normalise_triage(raw: str) -> str:
    low = raw.lower()
    for label, patterns in BUCKETS:
        for pattern in patterns:
            if re.search(pattern, low):
                return label
    return "intentional_design"


# --------------------------------------------------------------------------
# Gate bucketing. The gate token must start the cell.
#
# `D1_duplicate_check` was renamed from `P2_duplicate_check` in 0.2.0. `P2`
# means "privileged-role-gated" in the anti-pattern catalog; having the same
# token mean two different things across two repos was a documentation bug.
# --------------------------------------------------------------------------

GATE_RE = re.compile(r"^(5[0-9] (?:Gate [0-9]|Phase [0-9]|P[0-9]+)|5[0-9])")

GATE_LABELS = {
    "59 Phase 2": "D1_duplicate_check",
    "58 Gate 1": "G1_severity_floor",
    "58 Gate 2": "G2_exclusion_clause",
    "58 Gate 3": "G3_scope_tree",
    "58 Gate 4": "G4_prior_audit",
    "58 Gate 5": "G5_test_intent",
    "51": "design_review",
    "52": "program_ceiling",
    "57 P7": "P7_best_practice",
    "57 P12": "P12_no_persisted_impact",
    "57 P16": "P16_below_floor",
    "57 P17": "P17_no_attacker_win",
    "57 P18": "P18_design_tradeoff",
    "57 P19": "P19_headline_mismatch",
    "57 P20": "P20_cooperating_party",
}

VALID_GATES = set(GATE_LABELS.values()) | {"REALISM", "UNCLASSIFIED"}

#: The six gates runnable before you read target code. `D1_duplicate_check` is
#: listed with them because it is runnable pre-hunt - but only against a public
#: record (the program's known issues and its published audits), not against the
#: finding's prose.
PREHUNT_GATES = {
    "D1_duplicate_check",
    "G1_severity_floor",
    "G2_exclusion_clause",
    "G3_scope_tree",
    "G4_prior_audit",
    "G5_test_intent",
}

#: Gates answerable from a PUBLIC RECORD: the program's own pages, its published
#: audits, or its test suite.
PUBLIC_RECORD_GATES = {
    "G1_severity_floor",
    "G2_exclusion_clause",
    "G3_scope_tree",
    "G4_prior_audit",
    "G5_test_intent",
}


def normalise_gate(raw: str) -> str:
    stripped = raw.strip()
    match = GATE_RE.match(stripped)
    if match:
        return GATE_LABELS.get(match.group(1), "UNCLASSIFIED")
    if stripped.lower().startswith("realism"):
        return "REALISM"
    return "UNCLASSIFIED"


# --------------------------------------------------------------------------
# Root-cause bucketing.
#
# The private column is free text and routinely contains other researchers'
# handles and upstream finding IDs. It is NEVER passed through raw.
# --------------------------------------------------------------------------

ROOT_CAUSE_MAP: tuple[tuple[str, str], ...] = (
    (r"duplicate", "duplicate_known_family"),
    (r"known[- ]issue", "duplicate_known_family"),
    (r"privileged role", "oos_privileged_role"),
    (r"admin[- ]input", "admin_input_validation"),
    (r"scope (file )?tree|off-?chain", "oos_scope_boundary"),
    (r"exclusion", "oos_exclusion_clause"),
    (r"intentional design|by design|design tradeoff", "intentional_design"),
    (r"no attacker|self-harm|self-inflicted", "no_attacker_win"),
    (r"no fund loss|no net-positive|stuck", "no_fund_loss"),
    (r"severity floor|payout floor|below.*floor|program ceiling", "below_severity_floor"),
    (r"visibility", "function_visibility"),
    (r"prior audit|prior-audit", "prior_audit_known"),
    (r"\bgas\b|\bdos\b|denial", "gas_or_dos_only"),
    (r"third-party|oracle", "third_party_dependency"),
    (r"cooperating", "cooperating_party"),
    (r"spam|fabricated", "spam_fabricated_impact"),
    (r"config", "config_dependent"),
    (r"auxiliary|points|accounting field", "auxiliary_accounting"),
    (r"best[- ]practice", "best_practice"),
    (r"informational|no impact|no demonstrated impact", "no_demonstrated_impact"),
)

VALID_ROOT_CAUSE = {canonical for _, canonical in ROOT_CAUSE_MAP} | {"other"}


def normalise_root_cause(raw: str) -> str:
    low = (raw or "").lower()
    for pattern, canonical in ROOT_CAUSE_MAP:
        if re.search(pattern, low):
            return canonical
    return "other"


# --------------------------------------------------------------------------
# mechanism_class - a CLOSED VOCABULARY, derived here from the private source.
#
# This replaces the free-text `mechanism` column. It is classified from the
# private REPORT TITLE, which is the row's own statement of the mechanism, so
# the mapping is a property of the private record and not of an author's memory.
# Ordered: first match wins. Run with `--explain-classes` to print the
# assignment per row and audit it.
# --------------------------------------------------------------------------

MECHANISM_RULES: tuple[tuple[str, str], ...] = (
    ("secret_material_exposure", r"seed phrase|private key|credential|mnemonic|\bsecret"),
    ("approval_or_allowance_overwrite", r"approval|allowance"),
    ("callback_reentrancy_window", r"reentran|safe-?mint|callback"),
    ("signature_context_binding", r"signature (verification|binding)|zk-signature|signed .{0,60}binds no|binds no|signature authorization|signed withdrawal order"),
    ("replay_scope", r"replay|replayed|replayable|duplicate-utxo|nonce desync|nullifier"),
    ("input_length_validation_missing", r"short (flag|input)|slice[sd]? |buffer|\blength\b|malformed input"),
    ("slippage_protection_missing", r"slippage|sandwich"),
    ("boundary_condition_off_by_one", r"strict >|instead of >=|increments one beyond|off-by-one"),
    ("missing_zero_check", r"zero-check|zero check|division-by-zero|divides by|div-by-zero|without a zero"),
    ("no_op_state_transition", r"double-burn|dry_run|does not burn|deliberately (did not|does not)"),
    ("stale_cached_value", r"stale[- ]?(nav|cached)|cached (value|rate|price)|persists across"),
    ("unused_state_flag", r"stored but never|never enforced|is_isolated|zero effect|dual storage|shadow|gates .{0,20}but not"),
    ("key_binding_missing", r"caller-supplied|without the two|substitutes failed asset|not bound|\bunbound\b|arbitrary vault asset valuation|derives the address"),
    ("role_asymmetry", r"asymmetric|asymmetry|self-granted|admin account id"),
    ("parameter_bound_missing", r"unbounded|no upper bound|lower-bound|upper-bound|100x|permissive|non-ascending|zero-amount|zero-duration|duration=0|multiplier = 1|supply cap|accepts zero|missing validation"),
    ("missing_input_validation", r"missing .{0,20}validation|missing recipient|without a health check|zero-amount"),
    ("cross_boundary_message_ordering", r"async|outbound|message|commits? .{0,20}before|payload execution|reserves committed|failed (delivery|notification)"),
    ("oracle_bounds_or_staleness", r"oracle|price submission|stale price|future-timestamp|exchange rate|collateral price|stableswap|rate = 0|at par"),
    ("panic_without_persisted_impact", r"\bpanic|arithmetic (underflow|overflow)|aborts?\b"),
    ("accounting_bias_direction", r"shortchanges|systematically|bonus formula|regression|additive|round trip|extracts? (maker|inventory)|under-distribution|silently caps"),
    ("rounding_direction", r"rounding|round|truncat|ceil"),
    ("liveness_block", r"permanent|brick|freeze|frozen|unrecoverable|stuck|denial|\bdos\b|\block(s|ed|ing)?\b|\block\b|liveness|to collect"),
    ("missing_consent_or_authorisation", r"without consent|permissionless .{0,30}(triggers|blocks|convert)|self-destruct"),
    ("privileged_path_bypass", r"bypass|permissionless|anyone triggers|curator loop|operator gating|admin can|governance proposal|authority delegation|retroactively"),
    ("incomplete_state_predicate", r"missing .{0,20}guard|omitted|ignores the|\bempty\b|is_empty|health check"),
    ("token_classification_assumption", r"pair-to-pair|ispair|classification|blacklist|transfer hook|registered pair|pair pre-loading|lp liquidity"),
    ("accounting_order_of_operations", r"accounting|accumulator|ledger|bad_debt|overwrit|pro-rated|consumed the full|underflow|\bdebt\b|\bcei\b|over-pays|lastliquidationfees|desync|unfunded liquidity|pending add-liquidity|collect fees"),
    ("fee_base_or_ordering", r"\bfee|tax|commission"),
    ("reward_dilution", r"reward|dilution|emission|distribution|accrual|points|redistribution"),
    ("self_harm_precondition", r"self-liquidation|self-harm|self-inflicted|cooperating"),
    ("config_dependent", r"live config|documented config|deployed config|non-default|\bconfig\b"),
    ("incorrect_formula_or_constant", r"formula|constant|deviation|100%|99\.99%|2\u00d7"),
)

VALID_MECHANISM = {name for name, _ in MECHANISM_RULES} | {
    "other_mechanism",
    WITHHELD_MECHANISM,
}


#: `bug_family` - a closed vocabulary, assigned per row from the private record.
BUG_FAMILIES: tuple[str, ...] = (
    "access_control",
    "accounting",
    "async_ordering",
    "config",
    "fees",
    "governance",
    "input_validation",
    "liquidation",
    "liveness",
    "oracle",
    "panic",
    "reentrancy",
    "replay",
    "rewards",
    "rounding",
    "secrets",
    "signature_binding",
    "state_machine",
    "token_integration",
)

#: row -> bug_family. Authored from the private record; carries no target
#: information, because 19 families cover 97 rows.
ROW_BUG_FAMILY: dict[int, str] = {
    1: "state_machine", 2: "access_control", 3: "state_machine", 4: "panic",
    5: "secrets", 6: "signature_binding", 7: "rewards", 8: "liveness",
    9: "reentrancy", 10: "rewards", 11: "rewards", 12: "token_integration",
    13: "token_integration", 14: "oracle", 15: "panic", 16: "accounting",
    17: "input_validation", 18: "liquidation", 19: "state_machine", 20: "accounting",
    21: "accounting", 22: "rewards", 23: "input_validation", 24: "async_ordering",
    25: "async_ordering", 26: "input_validation", 27: "accounting", 28: "liveness",
    29: "accounting", 30: "config", 31: "config", 32: "access_control",
    33: "input_validation", 34: "access_control", 35: "accounting", 36: "config",
    37: "oracle", 38: "replay", 39: "governance", 40: "state_machine",
    41: "input_validation", 42: "config", 43: "accounting", 44: "rounding",
    45: "panic", 46: "async_ordering", 47: "async_ordering", 48: "async_ordering",
    49: "rewards", 50: "input_validation", 51: "rounding", 52: "oracle",
    53: "config", 54: "accounting", 55: "accounting", 56: "accounting",
    57: "liveness", 58: "input_validation", 59: "input_validation", 60: "state_machine",
    61: "input_validation", 62: "panic", 63: "signature_binding", 64: "accounting",
    65: "state_machine", 66: "input_validation", 67: "oracle", 68: "config",
    69: "token_integration", 70: "fees", 71: "liveness", 72: "config",
    73: "panic", 74: "liquidation", 75: "accounting", 76: "governance",
    77: "input_validation", 78: "liquidation", 79: "liveness", 80: "async_ordering",
    81: "async_ordering", 82: "oracle", 83: "reentrancy", 84: "token_integration",
    85: "fees", 86: "token_integration", 87: "token_integration", 88: "token_integration",
    89: "access_control", 90: "state_machine", 91: "replay", 92: "replay",
    93: "input_validation", 94: "access_control", 95: "accounting", 96: "config",
    97: "oracle",
}


# --------------------------------------------------------------------------
# family_id - opaque, script-assigned.
#
# A "family" is a set of submissions the private log ties to ONE bug family.
# The labels that justify each group are target-specific and stay private; what
# is published is the grouping and an opaque id, which is exactly what makes
# repeated submissions cluster visibly.
#
# Groups are the ones the private log states explicitly:
#
#   * identical report title                         (34/94, 35/95, 36/96, 54/56)
#   * identical root-cause family text               (46/47/48, 80/81)
#   * "same seam ... submitted two months earlier"   (91/92)
#   * "duplicate of the ... design limitation above" (84/86/87/88)
#   * one prior-audit finding covers both            (66/67)
#
# A family whose first submission is outside the log cannot be detected, so the
# recorded repeat count is a LOWER BOUND on self-duplication.
# --------------------------------------------------------------------------

FAMILY_GROUPS: tuple[tuple[int, ...], ...] = (
    (34, 94),
    (35, 95),
    (36, 96),
    (46, 47, 48),
    (54, 56),
    (66, 67),
    (80, 81),
    (84, 86, 87, 88),
    (91, 92),
)


def assign_families(published: list[int]) -> list[tuple[int, ...]]:
    """Return family groups over the published rows, in first-seen row order.

    First-seen means ordered by the lowest row index in each group, so F-001
    opens at the first published row and the ids run in file order. Grouping by
    "multi-row families first" would have been simpler to compute and harder to
    read.
    """
    allowed = set(published)
    groups: list[tuple[int, ...]] = []
    seen: set[int] = set()
    for group in FAMILY_GROUPS:
        rows = tuple(sorted(r for r in group if r in allowed))
        if rows:
            groups.append(rows)
            seen.update(rows)
    groups.extend((r,) for r in published if r not in seen)
    groups.sort(key=lambda g: g[0])
    return groups


# --------------------------------------------------------------------------
# duplicate_source - where the duplicate signal actually lived.
#
# Ordered: first match wins. `unknown` is a first-class value and its count is
# reported. Guessing here would be worse than admitting the log does not say.
# --------------------------------------------------------------------------

DUPLICATE_SOURCE_MAP: tuple[tuple[str, str], ...] = (
    # The author's own earlier submission, logged or not.
    (r"own prior|own-prior|unlogged|self-duplicate|own earlier|earlier outcome was unlogged|resubmitted the identical|submitted .{0,20}earlier", "own_prior"),
    # Somebody else found it at the same time.
    (r"\b60[- ]way|\b\d+ researchers|concurrent", "concurrent_submission"),
    # A public disclosure: a contest result, a published report, a paid bounty.
    (r"public(ly)? (disclos|report)|contest|bounty already paid|previously reported and resolved|novelty sweep", "public_disclosure"),
    # A published audit covered it.
    #
    # NO FIRM IS NAMED HERE. An earlier revision listed the firms that had
    # audited the author's targets by name, which is a disclosure: naming the
    # auditor narrows the target set. The pattern matches the SHAPE of an
    # audit reference - a prior audit, an audit finding, or a report id - and
    # never the firm.
    (r"prior audit|prior-audit|audit (finding|report|sweep|firm)|"
     r"(high|medium|low|critical)[- ]risk (finding|issue)|"
     r"previously reviewed on this program|remediation (was|landed)", "prior_audit"),
    # The team's own known-issues list, or an accepted-risk decision.
    (r"known[- ]issue|known .{0,20}family|already (reported|known|reviewed|accepted)|previously (reported|reviewed|raised|identified|evaluated)|accepted by the team|prior report|prior closeout|same root cause|same .{0,20}family|shared-symptom|known design", "known_issue"),
)

VALID_DUPLICATE_SOURCE = {
    "known_issue",
    "prior_audit",
    "public_disclosure",
    "concurrent_submission",
    "own_prior",
    "unknown",
    "not_duplicate",
    WITHHELD,
}


def classify_duplicate_source(triage_class: str, reason: str, root_cause: str) -> str:
    if triage_class != "duplicate":
        return "not_duplicate"
    text = f"{reason} {root_cause}".lower()
    for pattern, label in DUPLICATE_SOURCE_MAP:
        if re.search(pattern, text):
            return label
    return "unknown"


# --------------------------------------------------------------------------
# preventable_by - what would have stopped it, from the record.
#
#   public_record  readable from the program's own pages, its published audits,
#                  or its test suite (G1-G5), or from a public duplicate signal
#   own_log        only the author's own submission log could have caught it
#   none           nothing on file would have caught it; it needs the finding
#                  in hand and a judgement about it
#   unknown        the log does not support one of the above
# --------------------------------------------------------------------------

VALID_PREVENTABLE_BY = {"public_record", "own_log", "none", "unknown", WITHHELD}


def classify_preventable_by(gate: str, dup_source: str) -> str:
    if gate == "D1_duplicate_check":
        if dup_source == "own_prior":
            return "own_log"
        if dup_source in {"known_issue", "prior_audit", "public_disclosure"}:
            return "public_record"
        if dup_source == "concurrent_submission":
            return "none"
        return "unknown"
    if gate in PUBLIC_RECORD_GATES:
        return "public_record"
    if gate == "UNCLASSIFIED":
        return "unknown"
    return "none"


# --------------------------------------------------------------------------
# Structural patterns: things that identify a target or an internal artifact.
# --------------------------------------------------------------------------

BANNED_PATTERNS = [
    r"github\.com/",
    r"gitlab\.com/",
    r"\b[0-9a-f]{7,40}\b",  # commit hashes
    r"PROTOCOLS/",
    r"engagements/",
    r"submission_guides/",
    r"RESULTS/",
    r"\bF-\d{4}\b",
    r"\b[CMP]-\d{2}\b",
    r"-[Rr]\d\b",  # internal round suffixes
    r"\b20\d{2}-\d{2}-\d{2}\b",  # dates narrow the candidate set
]


@dataclass
class Blocklist:
    """Blocked tokens split by matching semantics.

    Proper nouns (platforms, chains, protocols, firms, contract names) are matched
    case-SENSITIVELY. They are capitalised in real prose, and matching them
    case-insensitively collides with ordinary English: "an almost-total denial"
    is not a reference to the chain, and "a sweep threshold" is not a function
    name. Case-sensitivity removes that whole class of false positive.

    Lowercase identifiers (module names, handles, finding-id prefixes, sponsor
    phrasing) are matched case-insensitively, because they are lowercase in the
    source and have no English collision.
    """

    case_sensitive: set[str]
    case_insensitive: set[str]

    def __len__(self) -> int:
        return len(self.case_sensitive) + len(self.case_insensitive)


def load_blocklist(path: Path) -> Blocklist:
    """Read the private blocklist, honouring its case-sensitivity groups."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        print("ERROR: PyYAML required.  pip install pyyaml", file=sys.stderr)
        raise SystemExit(2)

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    cs_groups = set(data.get("case_sensitive_groups") or [])
    ci_groups = set(data.get("case_insensitive_groups") or [])
    if not cs_groups and not ci_groups:
        # No grouping declared: treat everything as case-insensitive, which is the
        # stricter of the two and therefore fails safe.
        ci_groups = {k for k, v in data.items() if isinstance(v, list)}

    cs: set[str] = set()
    ci: set[str] = set()
    declaration_keys = {"case_sensitive_groups", "case_insensitive_groups"}
    for group, values in data.items():
        if group in declaration_keys or not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, str) or not value.strip():
                continue
            token = value.strip()
            if group in cs_groups:
                cs.add(token)
            elif group in ci_groups:
                ci.add(token)
            else:
                ci.add(token)

    if not cs and not ci:
        print(f"ERROR: blocklist {path} is empty - refusing to run", file=sys.stderr)
        raise SystemExit(2)
    return Blocklist(case_sensitive=cs, case_insensitive=ci)


def find_violations(text: str, banned: Blocklist) -> list[str]:
    """Return every blocked token present in `text`."""
    hits: list[str] = []
    low = text.lower()

    for token in sorted(banned.case_insensitive):
        if re.search(rf"\b{re.escape(token.lower())}\b", low):
            hits.append(f"token:{token}")

    for token in sorted(banned.case_sensitive):
        # Case-sensitive: the token must appear with its own capitalisation.
        if re.search(rf"\b{re.escape(token)}\b", text):
            hits.append(f"token:{token}")

    for pattern in BANNED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(f"pattern:{pattern}")
    return hits


def parse_private_db(path: Path) -> list[list[str]]:
    """Parse the private markdown table. Splits on unescaped pipes only."""
    rows: list[list[str]] = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Full Database"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("|"):
            continue
        if re.match(r"^\|\s*-", line) or re.match(r"^\|\s*(Protocol|Report)\b", line):
            continue
        cols = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cols) >= 7:
            rows.append(cols)
    return rows


def classify_mechanism(title: str) -> str:
    low = title.lower()
    for name, pattern in MECHANISM_RULES:
        if re.search(pattern, low):
            return name
    return "other_mechanism"


def build_rows(raw_rows: list[list[str]]) -> list[PublicRow]:
    # Family ids are assigned over the PUBLISHED rows only. A withheld row
    # publishes no family_id, so letting it consume an id would leave a gap in
    # the sequence and make the ids look like they had been redacted.
    published_indices = [
        i
        for i, cols in enumerate(raw_rows, start=1)
        if normalise_triage(cols[3]) != WITHHELD_TRIAGE
    ]
    groups = assign_families(published_indices)
    family_of: dict[int, str] = {}
    first_of: dict[int, int] = {}
    for index, group in enumerate(groups, start=1):
        fid = f"F-{index:03d}"
        for row_index in group:
            family_of[row_index] = fid
            first_of[row_index] = min(group)

    public: list[PublicRow] = []
    for i, cols in enumerate(raw_rows, start=1):
        _protocol, report, reason, triage_raw, gate_raw, root_cause, _fix = cols[:7]
        triage_class = normalise_triage(triage_raw)
        gate = normalise_gate(gate_raw)
        family = ROW_BUG_FAMILY.get(i, "other")
        if triage_class == WITHHELD_TRIAGE:
            public.append(
                PublicRow(
                    id=f"R-{i:03d}",
                    family_id=WITHHELD,
                    bug_family=family,
                    mechanism_class=WITHHELD_MECHANISM,
                    triage_class=triage_class,
                    earliest_gate=gate,
                    root_cause_class=normalise_root_cause(root_cause),
                    repeat_of_own=WITHHELD,
                    duplicate_source=WITHHELD,
                    preventable_by=WITHHELD,
                )
            )
            continue
        dup_source = classify_duplicate_source(triage_class, reason, root_cause)
        public.append(
            PublicRow(
                id=f"R-{i:03d}",
                family_id=family_of[i],
                bug_family=family,
                mechanism_class=classify_mechanism(report),
                triage_class=triage_class,
                earliest_gate=gate,
                root_cause_class=normalise_root_cause(root_cause),
                repeat_of_own="true" if i != first_of[i] else "false",
                duplicate_source=dup_source,
                preventable_by=classify_preventable_by(gate, dup_source),
            )
        )
    return public


# --------------------------------------------------------------------------
# Allowlist validation. Every published value must be a vocabulary member.
# --------------------------------------------------------------------------

ALLOWED: dict[str, set[str]] = {
    "bug_family": set(BUG_FAMILIES),
    "mechanism_class": VALID_MECHANISM,
    "triage_class": VALID_TRIAGE,
    "earliest_gate": VALID_GATES,
    "root_cause_class": VALID_ROOT_CAUSE,
    "repeat_of_own": {"true", "false", WITHHELD},
    "duplicate_source": VALID_DUPLICATE_SOURCE,
    "preventable_by": VALID_PREVENTABLE_BY,
}

FAMILY_ID_RE = re.compile(r"^F-\d{3}$")
ROW_ID_RE = re.compile(r"^R-\d{3}$")


def validate_rows(rows: list[PublicRow]) -> list[str]:
    problems: list[str] = []
    for row in rows:
        if not ROW_ID_RE.match(row.id):
            problems.append(f"{row.id}: bad row id")
        if row.family_id != WITHHELD and not FAMILY_ID_RE.match(row.family_id):
            problems.append(f"{row.id}: bad family_id {row.family_id!r}")
        for column, allowed in ALLOWED.items():
            value = getattr(row, column)
            if value not in allowed:
                problems.append(
                    f"{row.id}: {column} {value!r} is not in the allowed vocabulary"
                )
        # The withholding rule is structural, not advisory.
        if row.triage_class == WITHHELD_TRIAGE:
            if row.mechanism_class != WITHHELD_MECHANISM:
                problems.append(f"{row.id}: withheld row must ship {WITHHELD_MECHANISM}")
            for field in ("family_id", "repeat_of_own", "duplicate_source", "preventable_by"):
                if getattr(row, field) != WITHHELD:
                    problems.append(
                        f"{row.id}: withheld row leaks {field}={getattr(row, field)!r}"
                    )
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, help="private _REJECTION_DATABASE.md")
    ap.add_argument("--blocklist", type=Path, help="private redaction-blocklist.yaml")
    ap.add_argument("--out", type=Path, default=Path("data"))
    ap.add_argument("--check", action="store_true", help="verify an existing export")
    ap.add_argument(
        "--aggregates-only",
        action="store_true",
        help=(
            "publish only the summary tables, not the per-row category tuples. "
            "Use this if even category-level rows feel too close to a disclosure. "
            "The headline numbers are unaffected."
        ),
    )
    ap.add_argument(
        "--explain-classes",
        action="store_true",
        help="print the derived mechanism_class per row and exit",
    )
    args = ap.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)

    if args.check:
        return check_existing(args.out)

    if not args.source or not args.blocklist:
        ap.error("--source and --blocklist are required unless --check is given")

    banned = load_blocklist(args.blocklist)
    raw_rows = parse_private_db(args.source)
    if not raw_rows:
        print(f"ERROR: no rows parsed from {args.source}", file=sys.stderr)
        return 2

    public = build_rows(raw_rows)
    problems = validate_rows(public)

    # ---- FAIL-CLOSED VALIDATION -----------------------------------------
    violations: list[str] = []
    for row in public:
        payload = json.dumps(row.__dict__, ensure_ascii=False)
        for hit in find_violations(payload, banned):
            violations.append(f"{row.id}: {hit}")

    agg_text = " ".join(
        f"{k} {v}" for k, v in Counter(r.triage_class for r in public).items()
    )
    violations.extend(f"aggregate: {h}" for h in find_violations(agg_text, banned))

    if problems:
        print(f"\nREFUSING TO WRITE: {len(problems)} schema problems.\n", file=sys.stderr)
        for p in problems[:40]:
            print(f"  {p}", file=sys.stderr)
        print("\nNo files were written.", file=sys.stderr)
        return 2

    if violations:
        print(f"\nREFUSING TO WRITE: {len(violations)} banned tokens.\n", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print("\nNo files were written.", file=sys.stderr)
        return 1

    if args.explain_classes:
        for row in public:
            print(f"{row.id} {row.mechanism_class:<38} {row.bug_family:<20} {row.earliest_gate}")
        return 0

    # ---- WRITE ----------------------------------------------------------
    if not args.aggregates_only:
        with (args.out / "rejections.csv").open("w", newline="", encoding="utf-8") as fh:
            # Explicit LF: the default CRLF would fight .gitattributes on
            # every clone and make the generated data look modified.
            writer = csv.DictWriter(fh, fieldnames=list(COLUMNS), lineterminator="\n")
            writer.writeheader()
            for row in public:
                writer.writerow(row.__dict__)

        json_rows = []
        for row in public:
            obj = row.__dict__.copy()
            if obj["repeat_of_own"] in {"true", "false"}:
                obj["repeat_of_own"] = obj["repeat_of_own"] == "true"
            json_rows.append(obj)
        # newline="\n" for the same reason as the CSV writer: Windows text mode
        # would otherwise emit CRLF and fight .gitattributes on every clone.
        (args.out / "rejections.json").write_text(
            json.dumps(json_rows, indent=2) + "\n", encoding="utf-8", newline="\n"
        )

    # data/summary.json has ONE writer: scripts/stats.py. Both scripts import
    # the same compute() so the two can never disagree about what an aggregate
    # is; this script only calls it earlier, before the CSV exists on disk.
    summary = compute([r.__dict__ for r in public])
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    total = summary["total"]
    triage_counts = Counter(r.triage_class for r in public)
    catchable = summary["prehunt_catchable"]
    withheld_rows = summary["withheld_rows"]

    print(f"wrote {total} rows to {args.out}")
    for key, value in triage_counts.most_common():
        print(f"  {key:<22} {value:>4}  ({value / total:.1%})")
    print(f"\n  pre-hunt catchable: {catchable}/{total} ({100.0 * catchable / total:.1f}%)")
    print(f"  effective n (families): {summary['effective_n']}")
    print(f"  withheld rows: {withheld_rows}")
    print("\n  NOTE: no protocol, chain, ecosystem, date, severity or free text is published.")
    return 0


def check_existing(out: Path) -> int:
    """Re-validate an export on disk, with no private inputs available."""
    csv_path = out / "rejections.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found", file=sys.stderr)
        return 2

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    problems: list[str] = []

    if rows and list(rows[0].keys()) != list(COLUMNS):
        problems.append(f"columns are {list(rows[0].keys())}, expected {list(COLUMNS)}")

    for row in rows:
        for column, allowed in ALLOWED.items():
            if row.get(column) not in allowed:
                problems.append(
                    f"{row.get('id')}: {column} {row.get(column)!r} not in the allowlist"
                )
        if row.get("family_id") != WITHHELD and not FAMILY_ID_RE.match(row.get("family_id", "")):
            problems.append(f"{row.get('id')}: bad family_id")
        if row.get("triage_class") == WITHHELD_TRIAGE:
            for field in ("family_id", "repeat_of_own", "duplicate_source", "preventable_by"):
                if row.get(field) != WITHHELD:
                    problems.append(f"{row.get('id')}: withheld row leaks {field}")
        for pattern in BANNED_PATTERNS:
            if re.search(pattern, json.dumps(row), re.IGNORECASE):
                problems.append(f"{row.get('id')}: pattern:{pattern}")

    # The schema itself must not have grown a target dimension or free text.
    forbidden_columns = {
        "protocol",
        "protocol_class",
        "chain",
        "ecosystem",
        "language",
        "severity",
        "date",
        "mechanism",
        "paid",
    }
    leaked = forbidden_columns & set(rows[0].keys() if rows else [])
    if leaked:
        problems.append(f"schema exposes forbidden columns: {sorted(leaked)}")

    if problems:
        print(f"FAIL: {len(problems)} problems", file=sys.stderr)
        for p in problems[:40]:
            print(f"  {p}", file=sys.stderr)
        return 1

    print(f"OK: {len(rows)} rows, allowlist clean, no target dimension, no free text")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

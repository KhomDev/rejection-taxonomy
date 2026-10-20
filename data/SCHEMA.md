# Schema - data/rejections.csv / data/rejections.json

111 rows. One row per rejected submission. **Generated - never hand-edit.** Rebuild with
scripts/build_public_export.py.

## Columns

Ten columns. Nine are closed-vocabulary categories; one (id) is an ordinal. **There is no target
dimension and no free text.** Every published value must be a member of a vocabulary defined in
scripts/build_public_export.py. Validation is by **allowlist**: a value outside the vocabulary is a
build failure, not a warning.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | string | no | Stable row id, R-###. Synthetic; carries no information about the target. |
| family_id | enum | no | Opaque, script-assigned family grouping (F-###). Rows in one family are repeats of one bug. Withheld for redacted rows. |
| bug_family | enum | no | Closed vocabulary of 19 families. |
| mechanism_class | enum | no | 32 classes plus 2 sentinels. Derived from the private report title by the generator. |
| triage_class | enum | no | Normalised triage outcome. Six values. |
| earliest_gate | enum | no | The check that would have caught this before submission. |
| root_cause_class | enum | no | Closed-vocabulary reason the finding failed. other when unmapped. |
| repeat_of_own | bool | no | Whether this row repeats a family already present in the dataset. |
| duplicate_source | enum | no | Where the duplicate signal actually lived. Seven values. |
| preventable_by | enum | no | What could have stopped it. Four values. |

The literal value withheld appears in family_id, repeat_of_own, duplicate_source and preventable_by
for rows whose descriptive payload is withheld. See [What is withheld](#what-is-withheld).

### Why there is no free text

An earlier revision carried a free-text mechanism column, validated against a denylist. A denylist
cannot catch a paraphrase, so the hole was structural rather than a matter of a longer list. The
column is gone and every value is now drawn from a vocabulary, which means source text is never
passed through at all.

### Deliberately absent - and why

These exist in the private source and are **structurally excluded from the export**. The generator
fails closed if any reappears, and --check asserts the schema has not grown them back.

| Excluded | Why |
|---|---|
| protocol / protocol_class | Naming the target, or using a class that describes exactly one target, is a disclosure. |
| chain | **Restricted.** With this many rows, chain + ecosystem + outcome is a fingerprint. |
| ecosystem | Same reason. Language narrows a candidate set sharply. |
| language | Same. |
| report_title | Describes the specific bug; too identifying. |
| mechanism (free text) | Replaced by mechanism_class. |
| rejection_reason | Verbatim sponsor correspondence. Never reproduced. |
| submission_date | Narrows the candidate set. |
| severity_claimed / severity_assigned | Combined with outcome, narrows the target set. |
| module / function / line | Real symbols identify a codebase. |
| paid | Constant (always no). Replaced by a stated limitation: the dataset has no positive class. |
| source_row | Internal provenance hash, used only to trace a row back to the private DB. |

## Allowed values

### bug_family

| Family | Meaning |
|---|---|
| access_control | A caller-supplied key, slot or identifier not bound to the caller's authority |
| accounting | Value counted, credited, or discarded incorrectly |
| async_ordering | State committed across an asynchronous boundary in the wrong order |
| config | A parameter, constant or interval with no bound, or one that contradicts its docs |
| fees | Fee base, ordering or bypass |
| governance | Privileged or governance-mediated authority |
| input_validation | Caller-supplied input trusted without a check |
| liquidation | Liquidation math, ordering or incentive |
| liveness | A path that can be permanently blocked or made unreachable |
| oracle | Price or rate freshness, sourcing or manipulation |
| panic | A revert, panic or abort with no persisted consequence |
| reentrancy | Reentry through a callback |
| replay | A signed or authorised message reusable beyond its intended scope |
| rewards | Reward accrual, distribution or dilution |
| rounding | Precision, truncation or rounding-direction asymmetry |
| secrets | Credential or key material exposure |
| signature_binding | A signature verified without binding the fields that matter |
| state_machine | A flag, guard or state transition that does not do what it claims |
| token_integration | Behaviour arising from a token or pair-classification assumption |

### mechanism_class

Derived by the generator from the private report title, first matching rule wins.

The vocabulary has **34 members**: 32 mechanism classes, the `other_mechanism` residue, and the
`withheld_valid` sentinel. **33 are used** in the data: 32 across the 108 published rows, plus
`withheld_valid` on the three withheld rows. `other_mechanism` now holds 4 rows (it was empty
through 0.3.0). The three `below_payout_floor` rows ship `withheld_valid`.

accounting_bias_direction, accounting_order_of_operations, approval_or_allowance_overwrite,
boundary_condition_off_by_one, callback_reentrancy_window, config_dependent,
cross_boundary_message_ordering, fee_base_or_ordering, incorrect_formula_or_constant,
incomplete_state_predicate, input_length_validation_missing, key_binding_missing, liveness_block,
missing_consent_or_authorisation, missing_input_validation, missing_zero_check, no_op_state_transition,
oracle_bounds_or_staleness, other_mechanism, panic_without_persisted_impact, parameter_bound_missing,
privileged_path_bypass, replay_scope, reward_dilution, role_asymmetry, rounding_direction,
secret_material_exposure, self_harm_precondition, signature_context_binding,
slippage_protection_missing, stale_cached_value, token_classification_assumption, withheld_valid

**One class is a residue.** other_mechanism is the fallback when no rule matches. It was empty
through 0.3.0 and now holds 4 rows: a new row landed there rather than being forced into a
closer-but-wrong class, and that is visible in summary.json rather than hidden.

### triage_class

Bucketed by the **first matching rule** in this order. The order is load-bearing and mirrors the
private workspace's canonical stats script.

| Order | Value | Matched when the triage cell contains |
|---:|---|---|
| 1 | below_payout_floor | not paid, below payout, payout-floor, or a scope phrase of the form "out of scope for <name> payout" |
| 2 | spam | spam |
| 3 | duplicate | duplicate |
| 4 | out_of_scope | out of scope, oos |
| 5 | informational | inform |
| 6 | intentional_design | *(fallback - also absorbs Held and Not applicable)* |

> **Rule 1 is literal.** A bare unpaid does **not** match - only the patterns above. So
> Duplicate / unpaid buckets as duplicate, while Valid - Medium, NOT PAID buckets as
> below_payout_floor.
>
> **Rule 1's fourth pattern is deliberately generic.** The canonical private script matches one
> program-framework name as a literal string. That name is not published, so the equivalent is
> expressed as a pattern. It matches the same rows and no others - verified by the totals, which are
> unchanged.
>
> **Rule 6 is slightly lossy.** Held (post-mortem) rows fall through to intentional_design. "Held"
> means unresolved, not "intended". It is folded in to keep one source of truth; held is not a
> distinct public value. Three rows are affected.

### earliest_gate

The gate token must appear at the **start** of the private cell. Anything else becomes REALISM or
UNCLASSIFIED.

| Value | Meaning |
|---|---|
| D1_duplicate_check | Duplicate / known-family check. **Renamed from P2_duplicate_check in 0.2.0** - see CHANGELOG.md. |
| G1_severity_floor | Is there a payout tier at this severity? |
| G2_exclusion_clause | Does a program exclusion clause cover this? |
| G3_scope_tree | Is the root cause inside the scoped files? |
| G4_prior_audit | Is this surface already closed? |
| G5_test_intent | Does the project's own test suite assert this is intended? |
| design_review | Intentional design / no impact review |
| program_ceiling | Program-level severity ceiling |
| P7_best_practice | Best-practice critique |
| P12_no_persisted_impact | Revert-only, no persisted impact |
| P16_below_floor | Confirmed mechanics, below the severity floor |
| P17_no_attacker_win | No attacker-win / self-harm / no net-positive economics |
| P18_design_tradeoff | Design tradeoff |
| P19_headline_mismatch | Headline contradicted by PoC evidence |
| P20_cooperating_party | Requires a cooperating party |
| REALISM | Post-mortem realism gates (attacker-model, configuration, concession, PoC) |
| UNCLASSIFIED | No gate token recognised - investigate |

**The six pre-hunt gates** - D1_duplicate_check plus G1-G5 - account for 80 of 111 rows (72.1%).

There are **17 members** in the vocabulary: 16 gate values plus the `UNCLASSIFIED` sentinel. **13 are
used** in this dataset.

### duplicate_source

Where the duplicate signal actually lived. Assigned only when triage_class is duplicate; every other
row is not_duplicate. First matching rule wins, and unknown is a first-class value whose count is
reported rather than hidden.

| Value | Meaning | Rows |
|---|---|---:|
| not_duplicate | The row was not closed as a duplicate | 63 |
| known_issue | The team's own known-issues list, or an accepted-risk decision | 27 |
| unknown | The private log does not say, and guessing was not acceptable | 12 |
| withheld | The row's payload is withheld | 3 |
| prior_audit | A published audit covered it | 2 |
| public_disclosure | A contest result, a published report, or a paid bounty | 2 |
| concurrent_submission | Someone else found it at the same time | 1 |
| own_prior | The author's own earlier submission, logged or not | 1 |

**No audit firm is named by the classifier.** An earlier revision matched on the
names of the firms that had audited the author's targets, which is a disclosure:
naming the auditor narrows the target set. The pattern now matches the *shape* of
an audit reference and never the firm, which moved two rows between
`prior_audit` and `known_issue`.

**12 of 45 duplicate rows are unknown.** That is a real gap in the source record, and the honest
response is to publish the count rather than to guess a category.

### preventable_by

What would have stopped the rejection, from the record.

| Value | Meaning | Rows |
|---|---|---:|
| public_record | Readable from the program's own pages, its published audits or its test suite (G1-G5), or from a public duplicate signal | 60 |
| none | Nothing on file would have caught it; it needs the finding in hand and a judgement about it | 32 |
| unknown | The log does not support one of the above | 15 |
| withheld | The row's payload is withheld | 3 |
| own_log | Only the author's own submission log could have caught it | 1 |

This replaces the published claim that **73% were preventable before reading a line of code**. The
old figure counted every duplicate row, including one concurrent duplicate that cannot be pre-hunted
by anyone. See the README for the old figure, the new split, and why they differ.

### root_cause_class

Closed vocabulary. Anything unmapped becomes other, which is a signal to widen the map.

duplicate_known_family, oos_privileged_role, admin_input_validation, oos_scope_boundary,
oos_exclusion_clause, intentional_design, no_attacker_win, no_fund_loss, below_severity_floor,
function_visibility, prior_audit_known, gas_or_dos_only, third_party_dependency, cooperating_party,
spam_fabricated_impact, config_dependent, auxiliary_accounting, best_practice, no_demonstrated_impact,
other

## What is withheld

Rows with triage_class below_payout_floor ship **only** bug_family, triage_class, earliest_gate,
root_cause_class and mechanism_class = withheld_valid. Everything else is the literal value withheld.

The reason is that these are the dataset's **confirmed-valid** rows: a real bug, a working proof, a
team that agreed it was real, and a program whose reward table could not pay for it. They are the
most interesting rows here and also the most identifying, because "a confirmed-valid finding on a
program with a Critical-only floor" narrows the candidate set far more than a rejection does. The
aggregate counts are unaffected.

--aggregates-only goes further: it publishes the summary tables and drops the per-row tuples
entirely.

## Aggregates

Published as data/summary.json so consumers need not recompute. Generated by scripts/stats.py, which
also rewrites the generated block in the README.

| Metric | Value |
|---|---:|
| Rows | 111 |
| Withheld rows | 3 |
| **Effective n (distinct families)** | **96** |
| Rows repeating an earlier family | 12 |
| Families submitted more than once | 9 |
| Largest family | 4 |
| Duplicate | 45 (40.5%) |
| Out of scope | 26 (23.4%) |
| Informational | 20 (18.0%) |
| Intentional design | 16 (14.4%) |
| Below payout floor | 3 (2.7%) |
| SPAM | 1 (0.9%) |
| Pre-hunt-gate catchable | 80 (72.1%) |
| Analysis did not hold up - strict (spam only) | 1 (0.9%) |
| Analysis did not hold up - broad (spam + informational + intentional design) | 37 (33.3%) |

## Validation

    python scripts/build_public_export.py --check --out data/
    python scripts/stats.py --check

Asserts: every value is in its allowlist; no banned pattern (commit hash, repo URL, finding ID,
round suffix, date) appears in any field; every withheld row leaks no withheld field; the column set
is exactly the one documented above; and **the schema exposes no target dimension and no free text** -
the check fails if a column named protocol, protocol_class, chain, ecosystem, language, severity,
date, mechanism or paid ever reappears.

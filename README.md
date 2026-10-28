# rejection-taxonomy

**113 logged bug-bounty rejections, classified by triage outcome and by the earliest gate that
could have caught each one.**

The dataset contains **rejections only**. It has no positive class: there is no row for a finding
that was paid, because the private log this is derived from is a log of failures. Every proportion
below is a proportion *within a failure set*, and none of them is a success rate. That is a real
limitation, not a footnote - see [Known limitations](#known-limitations).

## What this is

A derived, redacted dataset. One row per rejected submission, reduced to categorical values:

    (bug family, mechanism class, triage outcome, earliest catchable gate,
     root cause class, whether it repeats an earlier family,
     where the duplicate signal lived, what could have prevented it)

Every value is a member of a closed vocabulary. There is no free text in the published data and no
target dimension: no protocol, no chain, no ecosystem, no date, no severity.

## What this is not

- **Not a survey.** n = 113, one researcher, four months, one target-selection process.
- **Not base rates.** It is a log of failures. It cannot yield a success rate, and it says nothing
  about how many submissions succeeded.
- **Not a filterable target dataset.** You cannot filter by chain, ecosystem, language or program,
  because those columns do not exist. That is deliberate.
- **Not a benchmark of anyone else's work.** The gate assignments are the author's own post-hoc
  judgement.

## Data dictionary

| File | What it is |
|---|---|
| `data/rejections.csv` | 113 rows, ten columns, all closed-vocabulary |
| `data/rejections.json` | the same rows, typed (`repeat_of_own` is a boolean here) |
| `data/summary.json` | every aggregate, computed by `scripts/stats.py` |
| `data/SCHEMA.md` | every column, every allowed value, and the bucketing rules |

```csv
id,family_id,bug_family,mechanism_class,triage_class,earliest_gate,root_cause_class,repeat_of_own,duplicate_source,preventable_by
R-091,F-080,replay,signature_context_binding,duplicate,D1_duplicate_check,duplicate_known_family,false,known_issue,public_record
R-021,F-021,accounting,accounting_order_of_operations,duplicate,program_ceiling,duplicate_known_family,false,known_issue,none
```

## Headline numbers

Every table in this section is generated. `scripts/stats.py` rewrites it from
`data/rejections.csv`, and the test suite fails if it has drifted. Do not hand-edit it.

<!-- BEGIN:generated -->

### Headline numbers

| Triage outcome | Count | Share |
|---|---:|---:|
| Duplicate / previously reported | 43 | 38.1% |
| Out of scope - boundary or exclusion clause | 26 | 23.0% |
| Informational - no security impact / no attacker profit | 24 | 21.2% |
| Intentional design / not a bug | 16 | 14.2% |
| Valid, but below the payout floor | 3 | 2.7% |
| SPAM - fabricated impact contradicted by the PoC | 1 | 0.9% |
| **Total** | **113** | **100%** |

**Effective n: 98 distinct bug families.** 113 rows are not 113 independent observations. 12 rows sit in 9 families that were submitted more than once (the largest family has 4 rows). A family whose first submission predates this log cannot be detected at all, so this is a lower bound on self-duplication.

### Where they died

| Earliest gate | Count | Share |
|---|---:|---:|
| `D1_duplicate_check` | 41 | 36.3% |
| `G2_exclusion_clause` | 20 | 17.7% |
| `P17_no_attacker_win` | 14 | 12.4% |
| `design_review` | 13 | 11.5% |
| `G4_prior_audit` | 7 | 6.2% |
| `G1_severity_floor` | 5 | 4.4% |
| `G3_scope_tree` | 4 | 3.5% |
| `REALISM` | 3 | 2.7% |
| `P16_below_floor` | 2 | 1.8% |
| `P19_headline_mismatch` | 1 | 0.9% |
| `program_ceiling` | 1 | 0.9% |
| `P20_cooperating_party` | 1 | 0.9% |
| `G5_test_intent` | 1 | 0.9% |

### What kind of bug each row was

| `mechanism_class` | Count |
|---|---:|
| `liveness_block` | 15 |
| `accounting_order_of_operations` | 8 |
| `parameter_bound_missing` | 8 |
| `oracle_bounds_or_staleness` | 7 |
| `accounting_bias_direction` | 6 |
| `privileged_path_bypass` | 5 |
| `token_classification_assumption` | 5 |
| `unused_state_flag` | 4 |
| `key_binding_missing` | 4 |
| `replay_scope` | 4 |
| `cross_boundary_message_ordering` | 4 |
| `missing_zero_check` | 4 |
| `other_mechanism` | 4 |
| `signature_context_binding` | 3 |
| `withheld_valid` | 3 |
| `role_asymmetry` | 2 |
| `reward_dilution` | 2 |
| `stale_cached_value` | 2 |
| `no_op_state_transition` | 2 |
| `panic_without_persisted_impact` | 2 |
| `missing_consent_or_authorisation` | 2 |
| `boundary_condition_off_by_one` | 2 |
| `missing_input_validation` | 2 |
| `config_dependent` | 2 |
| `rounding_direction` | 2 |
| `slippage_protection_missing` | 2 |
| `input_length_validation_missing` | 1 |
| `secret_material_exposure` | 1 |
| `approval_or_allowance_overwrite` | 1 |
| `self_harm_precondition` | 1 |
| `callback_reentrancy_window` | 1 |
| `fee_base_or_ordering` | 1 |
| `incorrect_formula_or_constant` | 1 |

### Where the duplicate signal lived

| `duplicate_source` | Count |
|---|---:|
| `not_duplicate` | 67 |
| `known_issue` | 25 |
| `unknown` | 12 |
| `withheld` | 3 |
| `prior_audit` | 2 |
| `public_disclosure` | 2 |
| `concurrent_submission` | 1 |
| `own_prior` | 1 |

### What could have prevented each rejection

| `preventable_by` | Count | Share |
|---|---:|---:|
| `public_record` | 58 | 51.3% |
| `none` | 36 | 31.9% |
| `unknown` | 15 | 13.3% |
| `withheld` | 3 | 2.7% |
| `own_log` | 1 | 0.9% |

### Did the analysis hold up?

| Definition | Numerator | Count | Share |
|---|---|---:|---:|
| **strict** - the impact was fabricated | `spam` | 1 | 0.9% |
| **broad** - no impact, intentional design, or fabricated | `spam` + `informational` + `intentional_design` | 41 | 36.3% |

An earlier version of this document used `informational` alone (21.2%) as the numerator and called the remaining 78.8% 'targeting'. That is not a definition: it is 100% minus one bucket, and it counts intentional-design rows as targeting failures when they are analysis failures. Both honest definitions are above.

<!-- END:generated -->

## Querying it

```bash
# what kinds of bugs were rejected as duplicates?
python scripts/query.py --triage duplicate

# the pre-hunt split
python scripts/query.py --prehunt

# rows that repeat an earlier family of my own
python scripts/query.py --repeats -v

# everything a public record could have stopped, before any code was read
python scripts/query.py --preventable-by public_record

# duplicate rows where the log does not say where the signal lived
python scripts/query.py --duplicate-source unknown

# one mechanism class
python scripts/query.py --mechanism-class replay_scope -v

# any filter, as JSON, for piping
python scripts/query.py --family oracle --json
```

There is no `--paid-only` flag and no `paid` column. Every row in this dataset was rejected, so
a filter for paid rows would return nothing by construction.

## Known limitations

Read these before quoting any number above.

1. **No positive class.** The dataset is a log of rejections. It contains no paid finding, so it
   cannot produce a success rate, a precision, or a base rate. Every proportion here is a
   proportion within a failure set.
2. **`earliest_gate` is self-assessed.** It is the author's post-hoc judgement of what *would*
   have caught the finding. It is not a record of what any tool said at the time, and a different
   analyst would assign some rows differently. It is the most useful column and the least objective
   one.
3. **Repeated families.** 12 of 113 rows repeat a family already in the dataset, so the effective
   sample is 98 families, not 113 rows. Cells with 1-2 rows are anecdotes, not rates.
4. **The rules that cite this dataset were derived from it.** The gate list and the
   `mechanism_class` vocabulary were built by reading these same rows. Any calibration against
   them is **in-sample**: it is closer to a ceiling than to an unbiased estimate.
5. **One researcher, four months, one selection process.** These are the programs the author chose
   to hunt. Target-selection habits - including the bad ones - are baked into every proportion.
6. **Selection bias is real and unquantified.** There is no comparison group.
7. **Self-assessed labels throughout.** `bug_family`, `root_cause_class`, `duplicate_source`
   and `preventable_by` are all classifications made by the same person who wrote the reports.
8. **`duplicate_source` and `preventable_by` have an `unknown` bucket, and it is populated.**
   12 of the 43 duplicate rows and 15 of 113 rows overall are `unknown`: the private log does not
   support a classification, and guessing was not acceptable. Those counts are reported rather than
   hidden.
9. **Rule drift.** Programs change their terms. A verdict reflects the rules in force at submission
   time, not today's.
10. **`below_payout_floor` rows are heavily redacted.** See the disclosure model below.

## Disclosure model - read this before citing

The dataset carries **no target dimension** and **no free text**.

An earlier draft of this repository published `chain` and `ecosystem`, on the theory that
withholding the protocol name was enough. It is not. With 113 rows across a few dozen targets,
`chain` + `ecosystem` + outcome + gate is a join key - a fingerprint, not an anonymisation. An
earlier revision then replaced those columns with a free-text `mechanism` description validated
against a denylist. That was better, but it was still a hole: a denylist cannot catch a paraphrase.
Both are gone.

**The current design validates by allowlist.** Every published value must be a member of a closed
vocabulary defined in `scripts/build_public_export.py` and documented in
[data/SCHEMA.md](data/SCHEMA.md). A value that is not in the vocabulary is a build failure, not a
warning. Source text is never passed through, so a private token cannot reach the output by
construction.

| Published | Never published |
|---|---|
| `id` - an ordinal, `R-###` | Protocol names, or any class that describes one |
| `family_id` - an opaque, script-assigned family grouping | Chain, ecosystem, or language |
| `bug_family` - a closed vocabulary of 19 families | Submission dates, or any date |
| `mechanism_class` - 32 classes, plus 2 sentinels (`other_mechanism`, `withheld_valid`) | Severity claimed or assigned |
| `triage_class` - a closed vocabulary of 6 outcomes | Verbatim sponsor correspondence |
| `earliest_gate` - 16 gates, plus the `UNCLASSIFIED` sentinel | Module names, function names, line numbers |
| `root_cause_class` - a closed vocabulary of 20 reasons | Finding IDs, commit hashes, repository paths |
| `repeat_of_own`, `duplicate_source`, `preventable_by` - closed vocabularies | Which programs were hunted at all |
| Aggregate counts | Any free-text description of a bug |

### What is withheld, and why

**The three `below_payout_floor` rows ship only five fields.** They are `bug_family`,
`triage_class`, `earliest_gate`, `root_cause_class` and `mechanism_class = withheld_valid`.
Everything else is the literal value `withheld`.

The reason is that these are the dataset's **confirmed-valid** rows: a real bug, a working proof, a
team that agreed it was real, and a program whose reward table could not pay for it. They are the
most interesting rows here and they are also the most identifying, because "a confirmed-valid
finding on a program with a Critical-only floor" narrows the candidate set far more than a rejection
does. A mechanism class plus a family id would say more about them than a rejection should. The
aggregate counts are unaffected.

`--aggregates-only` goes further: it publishes the summary tables and drops the per-row tuples
entirely. Every headline number is unchanged. The default ships the tuples because they let others
recompute the distributions themselves rather than trusting the author's arithmetic.

### Residual risk, stated honestly

Category tuples with no target axis disclose nothing about any specific program. That is the design
argument, and it is an argument, not a proof. Two residual risks remain:

- **The mechanism vocabulary is small.** 30 of its 32 classes are used across 94 published rows,
  and some classes have one member. A reader who already knows which programs the author hunts could narrow a single-row
  class. The mitigation is the `withheld` treatment above and `--aggregates-only`.
- **The author is not anonymous.** The repository is published under a handle, and the aggregate
  shape is a personal log. That is disclosed, not hidden.

If you believe a row identifies you or a program you work on, see [Takedown](#takedown).

## Reproducing

The public corpus is a **derived artifact**. It is generated from a private working database by a
redaction script that fails closed, and it is never hand-edited:

```bash
# regenerate the corpus (needs the private inputs)
python scripts/build_public_export.py \
    --source /path/to/private/_REJECTION_DATABASE.md \
    --blocklist /path/to/private/redaction-blocklist.yaml \
    --out data/

# regenerate every aggregate and the README tables
python scripts/stats.py

# verify both without any private input
python scripts/build_public_export.py --check --out data/
python scripts/stats.py --check
```

`build_public_export.py` refuses to write if any value falls outside the allowlist, if a withheld
row leaks a field, or if a blocked token survives into the output. **Never hand-edit `data/`** -
re-run the script.

The triage and gate bucketing mirrors the private workspace's canonical stats script exactly,
including bucket order, so published totals cannot drift from the source of truth.

### Gate rename: `P2_duplicate_check` -> `D1_duplicate_check`

In 0.2.0 the duplicate gate was renamed. `P2` means "privileged-role-gated" in the
[viability-gate](https://github.com/KhomDev/viability-gate) anti-pattern catalog, and having the
same token mean two different things across two repositories was a documentation bug. The rename is
applied to the data, the schema, the query tool and the tests. See `CHANGELOG.md`.

## Takedown

If you believe a row identifies you, your team, or a program you work on, open an issue using the
takedown template. Rows are removed on request, without argument and without requiring you to
justify it. The default is to comply.

Contact: `TODO(human): contact` (a real address has not been chosen yet; until it is, use the
GitHub issue tracker).

## How to cite

```bibtex
@dataset{khomdev_rejection_taxonomy,
  title  = {Bug-bounty rejection taxonomy: 113 logged submissions classified by triage outcome and earliest catchable gate},
  author = {KhomDev},
  year   = {2026},
  url    = {https://github.com/KhomDev/rejection-taxonomy},
  note   = {Rejections only; no positive class. One researcher; see limitations.}
}
```

A machine-readable `CITATION.cff` is in the repository root.

## Related

- [bounty-economics](https://github.com/KhomDev/bounty-economics) - the taxonomies of program
  payout tiers and exclusion clauses that make `G1_severity_floor` and `G2_exclusion_clause`
  mechanical
- [viability-gate](https://github.com/KhomDev/viability-gate) - the CLI that runs these checks
  against a draft finding, using *your* private ledger

Pin to a tag, not to `main`:
[rejection-taxonomy v0.5.0](https://github.com/KhomDev/rejection-taxonomy/tree/v0.5.0).

## License

| Path | License |
|---|---|
| `data/` (the published dataset) | CC-BY-4.0 |
| `scripts/`, `tests/` (code) | MIT |
| `docs/`, `README.md` (prose) | CC-BY-4.0 |
| `redaction-blocklist.PRIVATE.yaml` | not distributed; gitignored |

The [`LICENSE`](LICENSE) file in the repository root is the MIT text and nothing else, so tools
that detect licences read it correctly. The CC-BY-4.0 terms covering the dataset and the prose
(`docs/`, `README.md`), and their scope, are in [`LICENSE-DATA`](LICENSE-DATA), and are also
stated here and in `CITATION.cff`.

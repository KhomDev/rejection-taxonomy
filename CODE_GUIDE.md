# rejection-taxonomy - code guide

Accurate for release **v0.6.0** at main commit `4212b246e562f48c10814495e13737366ac5d8a5`. This
document is a line-level walkthrough of the code and data: the technical companion to
[README.md](README.md), which explains what the dataset is; this explains how every part of it works.
All `path:line` references were checked against that commit, where `git describe --tags --abbrev=0`
prints `v0.6.0` and `pyproject.toml:3` records `version = "0.6.0"`. Every count in this guide was
computed from `data/rejections.csv` at that commit and cross-checked against `data/summary.json`,
which `scripts/stats.py --check` proves is current.

## 1. Repository layout

The repository is a dataset with scripts, not an installable package. `pyproject.toml:11-14` says so,
and `[tool.setuptools]` ships no modules at all (`pyproject.toml:26-28`); `pip install ".[dev]"`
installs only the pinned tools - `pytest>=8,<10` and `ruff==0.17.0` (`pyproject.toml:16`).

| Path | Role |
|---|---|
| [data/](data) | The published dataset: `rejections.csv`, `rejections.json`, `summary.json`, `provenance.json`, and the prose schema `SCHEMA.md`. Generated; never hand-edited (`scripts/build_public_export.py:4`). |
| [scripts/](scripts) | Ten Python files: the vocabulary definitions, the public build, the aggregate generator, the query tool, and six checkers (Section 3). |
| [tests/](tests) | Six pytest files plus `fixtures/`: a synthetic 14-row classified input so the whole build runs with no private input. 129 tests, all passing at this commit. |
| [docs/](docs) | Three prose pages: `gates.md` (the six pre-proof-of-concept gates), `method.md` (how rows were classified), `patterns.md` (what the data says). |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | The CI pipeline: three jobs - `test`, `build`, `vocabulary` (Section 5). |
| [.github/ISSUE_TEMPLATE/](.github/ISSUE_TEMPLATE) | `correction.md` and `takedown-request.md`; the takedown template redirects reporters to private vulnerability reporting rather than a public issue. |
| [.github/dependabot.yml](.github/dependabot.yml) | Weekly, grouped dependency updates for pip and for the pinned GitHub Actions. |
| Root files | [README.md](README.md), [CHANGELOG.md](CHANGELOG.md), [CITATION.cff](CITATION.cff), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), the MIT [LICENSE](LICENSE), [LICENSE-DATA](LICENSE-DATA) (CC-BY-4.0 scope), `pyproject.toml`, `.gitattributes`, `.gitignore`. |

`pyproject.toml` also carries the tool configuration: pytest runs `tests/` with `scripts/` on the
import path (`pyproject.toml:30-33`); ruff uses line-length 100, targets Python 3.10, selects
`E,F,W,I,UP,B,C4,SIM` and ignores `E501` so long explanatory lines are legal (`pyproject.toml:35-44`);
`scripts/*.py` additionally ignore `B904` because `SystemExit` is not a handled exception
(`pyproject.toml:46-48`). The only runtime dependency is PyYAML (`pyproject.toml:6`), used by
`check_vocabulary.py` and by the private-input loaders; requires-python is >=3.10 (`pyproject.toml:5`).

`.gitattributes` is one line that matters: `* text=auto eol=lf` (`.gitattributes:1`). A UTF-8 byte-order
mark at the start of that file once made git ignore `eol=lf`, so every Windows clone came out CRLF and
the suite failed (`scripts/check_hygiene.py:6-8`); the BOM is gone, CI asserts a clean LF checkout
(`.github/workflows/ci.yml:43-48`), and `check_hygiene.py` fails on any BOM in any tracked file.

## 2. The dataset (data/)

### 2.1 Files

- `data/rejections.csv` - 113 data rows and a header at `data/rejections.csv:1`. Ten columns, every
  value closed-vocabulary except the `id` ordinal.
- `data/rejections.json` - the same 113 rows; `repeat_of_own` is a JSON boolean here
  (`scripts/build_public_export.py:332-339`), `true`/`false`/`withheld` in the CSV. `--check` fails
  unless the JSON matches the CSV cell for cell (`scripts/build_public_export.py:396-400`).
- `data/summary.json` - every published aggregate, one writer: `stats.write_summary`
  (`scripts/stats.py:126-130`).
- `data/provenance.json` - the SHA-256 digests of the private source, classifier and row ledger this
  release was built from, plus `removed_ids` (empty at this release, `data/provenance.json:5`). The
  four keys are fixed (`scripts/build_public_export.py:76`) and each digest must match
  `^[0-9a-f]{64}$` or be null (`scripts/build_public_export.py:80,131-133`).
- `data/SCHEMA.md` - the human-readable schema; parts of it are pinned to the data by
  `tests/test_data.py:186-220`.

### 2.2 Column schema

The ten columns, in file order, come from one tuple: `COLUMNS` at `scripts/vocab.py:13-24`. Their
semantics and allowed values:

| Column | Kind | Allowed values | Notes |
|---|---|---|---|
| `id` | ordinal | `R-###` (`scripts/build_public_export.py:78`) | Assigned once from a private ledger, never reused or renumbered (`data/SCHEMA.md:14`). |
| `family_id` | derived | `F-###` or `withheld` | Family grouping; numbered in first-seen order over published rows (Section 2.3). |
| `bug_family` | classified | 19 values (`scripts/vocab.py:46-51`) | Section 2.4. |
| `mechanism_class` | classified | 34 values: 32 classes plus `other_mechanism` and `withheld_valid` (`scripts/vocab.py:55-69`) | Assigned privately from the report title; one class per family (`data/SCHEMA.md:87-88`). |
| `triage_class` | classified | 6 values (`scripts/vocab.py:72-74`) | Section 2.4. |
| `earliest_gate` | classified | 17 values: 16 gates plus `UNCLASSIFIED` (`scripts/vocab.py:86-105`) | Section 2.4. |
| `root_cause_class` | classified | 20 values (`scripts/vocab.py:120-126`) | Unmapped causes fall to `other`. |
| `repeat_of_own` | derived | `true`, `false`, `withheld` (`scripts/vocab.py:144`) | Whether the row repeats a family of the author's already in the data. |
| `duplicate_source` | derived | 8 values (`scripts/vocab.py:131-134`) | Section 2.4. |
| `preventable_by` | derived | 5 values (`scripts/vocab.py:135`) | Section 2.4. |

**classified** columns are written by the private classifier; **derived** columns are computed inside
the public build from classified values only (`data/SCHEMA.md:25-27`). The allowlist wiring - column
to the exact value set - is the `ALLOWED` dict at `scripts/vocab.py:138-147`; a value outside it is a
build failure, not a warning.

### 2.3 id and family_id conventions

- Row ids match `^R-\d{3}$` (`scripts/build_public_export.py:78`) and are dense from `R-001`:
  `--check` builds the expected range and fails if any `R-###` in it is absent and not listed in
  `removed_ids` (`scripts/build_public_export.py:259-263`). At this commit the data runs `R-001` to
  `R-113` with no gaps and `removed_ids` is empty, so all 113 ids are published.
- Family ids match `^F-\d{3}$` (`scripts/build_public_export.py:79`). They are assigned in first-seen
  order over the **published** rows only - a withheld row consumes no id, so the sequence has no
  tell-tale gap (`scripts/build_public_export.py:197-203`). `--check` re-derives the order and fails
  if a family opens out of sequence, if a first row is not `repeat_of_own=false`, or if a later row is
  not `true` (`scripts/build_public_export.py:293-303`).
- A family is one bug: every member shares one `bug_family` and one `mechanism_class`, enforced at
  classification time (`scripts/build_public_export.py:180-186`) and again on published rows
  (`scripts/build_public_export.py:318-323`).
- Family ids do not track row ids. F-080, for example, opens at R-091
  (`data/rejections.csv:92`) with `repeat_of_own=false`; R-092 (`data/rejections.csv:93`) repeats
  it. Numbering is positional over first-seen order, not derived from the row's own id.

Computed at this commit: 110 rows publish a family and carry 98 distinct family ids. Family-size
histogram: 89 singletons, 7 pairs, 1 triple (F-046: R-046, R-047, R-048 at
`data/rejections.csv:47-49`), 1 quadruple (F-077: R-084 at `data/rejections.csv:85` plus R-086,
R-087, R-088 at `data/rejections.csv:87-89` - all `token_integration` /
`token_classification_assumption`). Twelve rows repeat a family, listed by the generated README block;
by `repeat_of_own` the data holds 98 `false`, 12 `true`, 3 `withheld`.

### 2.4 The closed vocabularies, exactly as the code defines them

Source of truth: `scripts/vocab.py`. The tables below add a count column computed from
`data/rejections.csv` at this commit.

**bug_family** - 19 values (`scripts/vocab.py:46-51`), all used:

| Value | Rows |
|---|---:|
| `accounting` | 18 |
| `input_validation` | 14 |
| `liveness` | 9 |
| `config` | 8 |
| `access_control` | 7 |
| `async_ordering` | 7 |
| `state_machine` | 7 |
| `token_integration` | 7 |
| `oracle` | 6 |
| `panic` | 5 |
| `rewards` | 5 |
| `fees` | 4 |
| `liquidation` | 3 |
| `replay` | 3 |
| `signature_binding` | 3 |
| `governance` | 2 |
| `reentrancy` | 2 |
| `rounding` | 2 |
| `secrets` | 1 |

**mechanism_class** - 32 classes (`scripts/vocab.py:55-67`) plus two sentinels: `other_mechanism`, the
residue when no rule matched, defined at `scripts/vocab.py:68`, and `withheld_valid`, the withholding
sentinel at `scripts/vocab.py:33`. `VALID_MECHANISM` is the union: 34 values (`scripts/vocab.py:69`).
Computed: 33 of the 34 values occur; 31 of the 32 classes carry at least one row, matching
`mechanism_classes_used` in `data/summary.json:120`; 7 classes are used by exactly one row
(`singleton_mechanism_classes`, `data/summary.json:121`). The one class no row uses is
`incomplete_state_predicate`.

| Value | Rows |
|---|---:|
| `liveness_block` | 15 |
| `accounting_order_of_operations` | 8 |
| `parameter_bound_missing` | 8 |
| `oracle_bounds_or_staleness` | 7 |
| `accounting_bias_direction` | 6 |
| `privileged_path_bypass` | 5 |
| `token_classification_assumption` | 5 |
| `cross_boundary_message_ordering` | 4 |
| `key_binding_missing` | 4 |
| `missing_zero_check` | 4 |
| `other_mechanism` (sentinel) | 4 |
| `signature_context_binding` | 4 |
| `unused_state_flag` | 4 |
| `replay_scope` | 3 |
| `withheld_valid` (sentinel) | 3 |
| `boundary_condition_off_by_one` | 2 |
| `config_dependent` | 2 |
| `missing_consent_or_authorisation` | 2 |
| `missing_input_validation` | 2 |
| `no_op_state_transition` | 2 |
| `panic_without_persisted_impact` | 2 |
| `reward_dilution` | 2 |
| `role_asymmetry` | 2 |
| `rounding_direction` | 2 |
| `slippage_protection_missing` | 2 |
| `stale_cached_value` | 2 |
| `approval_or_allowance_overwrite` | 1 |
| `callback_reentrancy_window` | 1 |
| `fee_base_or_ordering` | 1 |
| `incorrect_formula_or_constant` | 1 |
| `input_length_validation_missing` | 1 |
| `secret_material_exposure` | 1 |
| `self_harm_precondition` | 1 |
| `incomplete_state_predicate` | 0 |

**triage_class** - 6 values, in the private bucketing order (first matching rule wins)
(`scripts/vocab.py:72-74`), with the display labels from `TRIAGE_LABELS` (`scripts/vocab.py:76-83`):

| Value | Label | Rows |
|---|---|---:|
| `duplicate` | Duplicate / previously reported | 43 |
| `out_of_scope` | Out of scope - boundary or exclusion clause | 26 |
| `informational` | Informational - no security impact / no attacker profit | 24 |
| `intentional_design` | Intentional design / not a bug | 16 |
| `below_payout_floor` | Valid, but below the payout floor | 3 |
| `spam` | SPAM - fabricated impact contradicted by the PoC | 1 |

**earliest_gate** - `VALID_GATES` is the key set of `GATE_MEANING` (`scripts/vocab.py:86-105`): 16
gates plus the `UNCLASSIFIED` sentinel, 17 values. Meanings below are quoted from `GATE_MEANING`.

| Value | What the gate asks | Rows |
|---|---|---:|
| `D1_duplicate_check` | is this already a known issue, a prior audit finding or a public disclosure? | 41 |
| `G1_severity_floor` | is there a payout tier at this severity? | 5 |
| `G2_exclusion_clause` | does an exclusion clause cover this? | 20 |
| `G3_scope_tree` | is the root cause inside the scoped files? | 4 |
| `G4_prior_audit` | is this surface already closed by a published audit? | 7 |
| `G5_test_intent` | does the project's test suite assert this is intended? | 1 |
| `design_review` | intentional design / no impact review | 13 |
| `program_ceiling` | program-level severity ceiling | 1 |
| `P7_best_practice` | best-practice critique | 0 |
| `P12_no_persisted_impact` | revert-only, no persisted impact | 0 |
| `P16_below_floor` | confirmed mechanics, below the severity floor | 2 |
| `P17_no_attacker_win` | no attacker-win / self-harm / no net-positive economics | 14 |
| `P18_design_tradeoff` | design tradeoff | 0 |
| `P19_headline_mismatch` | headline contradicted by PoC evidence | 1 |
| `P20_cooperating_party` | requires a cooperating party | 1 |
| `REALISM` | realism gates (attacker-model, config, concession) | 3 |
| `UNCLASSIFIED` | no gate token recognised | 0 |

Computed: 13 of the 17 values occur. `P18_design_tradeoff` is a known id collision with
viability-gate and is additionally banned from use by `scripts/check_vocabulary.py:100-105`.
Two subsets matter downstream: `PUBLIC_RECORD_GATES` is G1-G5 (`scripts/vocab.py:110-112`) and
`PREHUNT_GATES` adds D1 (`scripts/vocab.py:118`) - the six gates the
[viability-gate](https://github.com/KhomDev/viability-gate) CLI runs before a proof of concept.

**root_cause_class** - 20 values (`scripts/vocab.py:120-126`). Computed counts (this distribution is
published nowhere else; `data/summary.json:119` records only the total for `other`):

| Value | Rows |
|---|---:|
| `duplicate_known_family` | 42 |
| `no_attacker_win` | 17 |
| `intentional_design` | 14 |
| `other` | 11 |
| `no_demonstrated_impact` | 7 |
| `below_severity_floor` | 3 |
| `gas_or_dos_only` | 3 |
| `oos_privileged_role` | 3 |
| `admin_input_validation` | 2 |
| `config_dependent` | 2 |
| `oos_scope_boundary` | 2 |
| `auxiliary_accounting` | 1 |
| `best_practice` | 1 |
| `function_visibility` | 1 |
| `oos_exclusion_clause` | 1 |
| `prior_audit_known` | 1 |
| `spam_fabricated_impact` | 1 |
| `third_party_dependency` | 1 |
| `cooperating_party` | 0 |
| `no_fund_loss` | 0 |

Computed: 18 of the 20 values occur; `cooperating_party` and `no_fund_loss` are unused.

**duplicate_source** - built from the signal sets: `PUBLIC_DUP_SIGNALS` is {known_issue, prior_audit,
public_disclosure} (`scripts/vocab.py:131`); `DUP_SIGNALS` adds {concurrent_submission, own_prior,
unknown, none} (`scripts/vocab.py:132`); the published value set is that minus `none` plus
{not_duplicate, withheld} - 8 values (`scripts/vocab.py:134`). Computed rows: `not_duplicate` 67,
`known_issue` 25, `own_prior` 7, `unknown` 6, `withheld` 3, `prior_audit` 2, `public_disclosure`
2, `concurrent_submission` 1. The value is a duplicate marker exactly when `triage_class` is
`duplicate` (`scripts/build_public_export.py:305-307`).

**preventable_by** - {public_record, own_log, none, unknown, withheld} (`scripts/vocab.py:135`).
Computed rows: `public_record` 63, `none` 31, `own_log` 9, `unknown` 7, `withheld` 3.

### 2.5 Derived columns: the two rules

`duplicate_source` comes from `derive_duplicate_source(triage, dup_signal, repeat_of_own)`
(`scripts/vocab.py:150-161`): a non-duplicate is `not_duplicate`; a duplicate takes the signal the
private log names; a duplicate whose log names no usable signal but which repeats one of the author's
own families is `own_prior`; otherwise `unknown`.

`preventable_by` comes from `derive_preventable_by(gate, dup_signal, repeat_of_own)`
(`scripts/vocab.py:164-185`), cheapest source first:

1. a public duplicate signal (known issue, prior audit, public disclosure) - `public_record`;
2. a gate answerable from the program's public record (G1-G5) - `public_record`;
3. the row repeats an earlier family of the author's, or the log says it duplicated one - `own_log`;
4. a concurrent duplicate - `none`;
5. a D1 or unrecognised gate with no recorded signal - `unknown`;
6. anything else - `none`.

The published data is re-checked against these rules wherever the other columns determine the answer
(`scripts/build_public_export.py:309-316`), and a duplicate that repeats the author's own family can
never be `unknown` (`scripts/build_public_export.py:315-316`). Both rules are pinned case by case in
`tests/test_build.py:238-266`.

### 2.6 Withholding and redaction

- Rows whose `triage_class` is `below_payout_floor` (`WITHHELD_TRIAGE`, `scripts/vocab.py:32`) ship
  only `bug_family`, `triage_class`, `earliest_gate`, `root_cause_class` and
  `mechanism_class = withheld_valid`; `family_id`, `repeat_of_own`, `duplicate_source` and
  `preventable_by` are the literal `withheld` (`WITHHELD_FIELDS`, `scripts/vocab.py:34`). The build
  constructs them that way (`scripts/build_public_export.py:207-218`), validates the shape
  (`scripts/build_public_export.py:277-283`), and separately rejects any `withheld` value on a row
  that is not withheld (`scripts/build_public_export.py:285-288`).
- At this commit exactly three such rows exist: R-064 (`data/rejections.csv:65`), R-070
  (`data/rejections.csv:71`) and R-085 (`data/rejections.csv:86`).
- The schema is checked against target dimensions: if any of the 19 forbidden column names in
  `FORBIDDEN_COLUMNS` appears - protocol, chain, ecosystem, language, date, severity, module,
  function, line, mechanism, paid, report titles, sponsor correspondence, private row keys
  (`scripts/vocab.py:37-44`) - the build fails (`scripts/build_public_export.py:248-250`).
- Belt and braces on top of the allowlist, `BANNED_PATTERNS` rejects any row cell matching a URL, a
  7-40 hex-digit commit-hash shape, a date, or a path (`scripts/build_public_export.py:85-90`), applied
  per row (`scripts/build_public_export.py:272-275`).
- The build has two stages (`scripts/build_public_export.py:5-28`). The private classifier reads the
  private log and writes vocabulary values only; the public build in this repository never sees
  private text. The classifier keys rows by a stable hash so inserting rows into the private log
  cannot shift a classification onto the wrong row (`scripts/build_public_export.py:14-16`),
  re-stated in `docs/method.md:35-38`. Until 0.5.1 the classifier was published here; the history was
  reset for 0.6.0 to remove it (`CHANGELOG.md:23-38`).

### 2.7 Invariants, and how they are enforced

`--check --out data/` re-validates the published export with no private input
(`scripts/build_public_export.py:376-408`): it re-reads `rejections.csv`, validates provenance
(`:385-392`), runs `validate_published` over every row (`:394`), and fails unless `rejections.json`
equals `rejections.csv` cell for cell (`:396-400`). Exit codes: 0 ok, 1 validation failed, 2 cannot
run (`scripts/build_public_export.py:42`). At this commit it prints
`OK: 113 rows, allowlist clean, invariants hold, no target dimension, no free text`. The full
invariant list - allowlist membership, banned shapes, dense ids, the withholding rule, family ordering
and coherence, the duplicate marker, the preventable_by consistency rules, JSON equality - is
`validate_published` (`scripts/build_public_export.py:242-324`), restated in `data/SCHEMA.md:245-256`.

## 3. scripts/ - script by script

### 3.1 scripts/vocab.py (186 lines)

One definition of every vocabulary, imported by the build, the aggregates, the query tool, the
vocabulary cross-check and the tests (`scripts/vocab.py:1-8`). Exports: the column tuple `COLUMNS`
(`:13-24`), the withholding constants (`:27-34`), `FORBIDDEN_COLUMNS` (`:37-44`), the five closed
vocabularies plus the dup-signal and preventable sets (`:46-135`), the `ALLOWED` wiring
(`:138-147`), and the two derivation functions of Section 2.5. Nothing in it is derived from or
describes any private record (`:6-7`).

### 3.2 scripts/build_public_export.py (455 lines)

The public build and the `--check` re-validator.

- `INTERMEDIATE_COLUMNS` (`:72-75`) is the private classifier's CSV shape: id, family, bug_family,
  mechanism_class, triage_class, earliest_gate, root_cause_class, dup_signal.
- `read_classified(path: Path) -> list[dict]` (`:106-113`) refuses any header that is not exactly
  that order.
- `read_provenance(path: Path | None) -> dict` (`:116-123`) and
  `validate_provenance(data: dict) -> list[str]` (`:126-137`): exactly the four keys, SHA-256 or
  null, `removed_ids` a list of `R-###`.
- `validate_classified(rows, removed) -> list[str]` (`:140-187`): id shape, uniqueness and order
  (`:145-152`); density against published-plus-removed ids (`:153-159`); per-column allowlist and
  dup-signal membership (`:162-167`); `withheld_valid` only on a `below_payout_floor` row
  (`:168-169`); family references resolve to in-file rows (`:170-179`), family roots precede
  members, and members share the family's bug_family and mechanism_class (`:180-186`).
- `build_rows(rows) -> list[dict]` (`:195-234`): drops withheld rows from family numbering
  (`:197-203`), emits the withheld row shape (`:207-218`), computes `repeat_of_own` from
  `family != id` (`:219`), and derives the two remaining columns through the `vocab.py` rules
  (`:230-231`).
- `validate_published(rows, removed=None) -> list[str]` (`:242-324`): the invariant list of
  Section 2.7, plus the banned-pattern scan and family-opening order.
- `write_outputs(rows, provenance, out, aggregates_only)` (`:348-363`): writes the CSV with LF
  line endings (`:356-359`), the JSON and provenance through `write_text_lf` (`:342-345`, whose
  comment explains the Windows text-mode trap), and delegates `summary.json` to the one shared
  writer (`:362-363`). With `--aggregates-only` it also deletes any per-row files left in `--out`
  by an earlier build (`:351-354`).
- `check_existing(out: Path) -> int` (`:376-408`) and `main(argv) -> int` (`:411-451`): `--check`
  short-circuits (`:427-428`); without `--classified` the run stops with exit 2 (`:429-431`);
  any validation problem means nothing is written and exit 1 (`:438-443`); success prints the
  per-triage split of the build (`:446-449`).

Verified at this commit: the fixture build writes 14 rows and passes `--check`; the same build with
`--aggregates-only` leaves only `summary.json` and `provenance.json`; a run with no arguments
exits 2 with the usage error `--classified is required unless --check is given`.

### 3.3 scripts/stats.py (296 lines)

Every published aggregate.

- `compute(data: list[dict]) -> dict` (`:61-119`) counts the six distributions plus the composite
  figures: `prehunt_catchable` (rows whose gate is in `PREHUNT_GATES`, `:77`),
  `public_record_preventable` (`:78`), the strict/broad analysis split from `STRICT_ANALYSIS` /
  `BROAD_ANALYSIS` (`:41-42`, summed at `:75-76`), and the identifiability measures over
  `TUPLE_COLUMNS` (`:45`): distinct families over rows with a family (`:70-73`), repeat rows,
  repeated families and the largest family, singleton mechanism classes (`:116-117`) and unique
  five-column category tuples (`:118`). The key order is part of the published format: the keys up
  to `analysis_split` are the 0.5.x keys, unchanged, and 0.6.0 appends after them (`:83-85`).
- `write_summary(data, path) -> dict` (`:126-130`) is the only code that writes `summary.json`; both
  this script and the build call it, so the two paths cannot disagree.
- `render(agg: dict) -> str` (`:133-234`) produces the six generated README sections; the generated
  block is delimited by `BEGIN`/`END` markers (`:35-36`).
- `apply_readme(block, check) -> bool` (`:237-251`) compares and rewrites by BYTES (`:247`), so a
  CRLF checkout of README reads as stale (`:279-284` echoes that hint on failure).
- `main(argv) -> int` (`:254-292`): `--json` prints the aggregate object (`:263-265`); `--check`
  exits 1 with a `STALE` line per drifted artifact (`:274-286`); the default rewrites both.

Verified: `--check` prints `OK: summary.json and README are current (113 rows)`; `--json` begins
`total: 113, prehunt_catchable: 78, prehunt_catchable_pct: 69.0, withheld_rows: 3, effective_n: 98`.

### 3.4 scripts/query.py (181 lines)

- `load() -> list[dict]` (`:42-48`) exits 2 if the CSV is missing.
- Every value filter is an `argparse` choice drawn from `sorted(ALLOWED[column])` (`:113-122`), so a
  typo is an error, not an empty result. Six value filters plus `--repeats`, `--prehunt` (gate in
  `PREHUNT_GATES`) and `--posthunt` (gate not in it) combine with AND (`:150-170`).
- `overview(rows)` (`:62-85`) prints the triage/family/mechanism distributions, the gate list with a
  `*` marking the six pre-proof-of-concept gates (`:71-75`), the prehunt total, the public-record
  preventable share (`:77-81`), effective n over published rows (`:83-84`) and the repeat-row count.
- `show_rows(rows, verbose)` (`:88-108`) prints one or two lines per row; `--json` emits the
  matching rows (`:172-174`).

Verified: the overview prints `earliest gate is one of the six: 78/113 (69.0%)`,
`preventable from the public record: 63/113 (55.8%)`, `effective n: 98 distinct bug families`,
`rows repeating an earlier family: 12`; `--repeats` returns 12 rows; `--posthunt` returns 35;
an unknown filter value exits 2 with `invalid choice`.

### 3.5 scripts/check_vocabulary.py (143 lines)

Cross-repository id discipline, born from the `P2` collision (`:5-13`).

- `PINNED_VG_TAG = "v0.5.0"` (`:38`) is the one place the viability-gate version is pinned, so a new
  viability-gate release cannot turn this check red retroactively.
- `SHARED_IDS` (`:41-54`) maps 12 published gate values to (viability-gate id, expected title);
  `KNOWN_COLLISIONS` (`:57-59`) holds the one known break, `P18_design_tradeoff`.
- `check(titles, counts) -> list[str]` (`:89-108`): (a) every gate-like vocabulary value must be
  mapped here (`:91-94`); (b) each mapped id must exist in viability-gate with the exact expected
  title (`:95-99`); (c) a known-collision value must have zero rows (`:100-105`); (d)
  `P2_duplicate_check` must never return (`:106-107`).
- `load_titles(vg)` (`:70-78`) reads `rules/gates.yaml` and `rules/anti-patterns.yaml` with
  PyYAML; `published_counts()` (`:81-86`) reads the gate column of the real data.
- `sibling_dir` (`:62-67`) resolves `--viability-gate`, else `$VIABILITY_GATE_DIR`, else
  `../viability-gate`; a missing sibling is SKIP, or exit 2 under `--require` (`:121-128`).

Verified: against a checkout of viability-gate at `v0.5.0` the checker prints
`OK: 12 shared ids agree with viability-gate at _viability-gate; 1 known collision unused`.

### 3.6 scripts/check_hygiene.py (271 lines)

Four checks (`:5-15`): UTF-8 encoding without BOM or mojibake; no private-workspace paths; and, only
with the private inputs, tripwire tokens and a full git-history scan. CI runs `--no-history`
(`.github/workflows/ci.yml:59-60`); the tripwire and history scans SKIP there and the maintainer runs
them before every release (the workflow comment at `.github/workflows/ci.yml:56-58`; the skip
logic at `scripts/check_hygiene.py:237-252`).

- `iter_files() -> list[Path]` (`:72-94`) uses `git ls-files --cached --others --exclude-standard`,
  so gitignored private inputs are never scanned as leaks; the fallback walk skips bin dirs
  (`:42`, `:92-94`).
- `check_encoding(files) -> list[str]` (`:108-125`): binary is skipped via a NUL byte in the first
  8000 (`:113-114`); then UTF-8 decode, a BOM check (`:120-121`) and the cp1252 round-trip
  mojibake sequences listed at `:51-60`. The `.gitattributes` BOM story is the reason this
  check exists (`:6-8`).
- `check_private(files) -> list[str]` (`:128-141`) scans for the six private-workspace path tokens
  defined at `:63` - this guide deliberately does not repeat them. `PRIVATE_ALLOWED` (`:66-69`)
  exempts exactly the checker itself and its test.
- `check_tripwires(files, compiled)` (`:144-153`) applies the private tripwire list through
  `token_scan`; loaded from `--private-dir` or `$RT_PRIVATE_DIR` (`:218-220`, `:238-245`).
- `load_blocklist(path) -> (cs, ci)` (`:156-175`): YAML mapping; undeclared groups are
  case-insensitive, the stricter default (`:157-158`).
- `check_history(cs, ci, compiled) -> list[str]` (`:191-215`): every commit reachable from any ref,
  every blob once, every commit and tag message - and the report counts tokens without ever printing
  one (`:208-210`).

Verified: `--no-history` before this guide existed printed two SKIP lines and
`OK: 40 files - encoding, private clean`; with this guide tracked it reports 41 files, still clean
(`--json` shows `files_scanned: 41` and empty `encoding`/`private` arrays).

### 3.7 scripts/token_scan.py (70 lines)

The tripwire matcher, shared by the hygiene checker and its tests so the check the author runs and
the check the tests pin are the same function (`:3-5`, pinned by `tests/test_token_scan.py:66-67`).

- `pattern(token)` (`:36-40`): a token counts only standing alone; lookaround boundaries are added
  on each word-character end, and a prefix token such as `abc-` gets no trailing boundary because
  none can exist there (`:20-25`).
- `compile_tokens(tokens)` (`:43-45`); `load_tokens(path)` (`:48-56`) expects a YAML `tokens:`
  list and refuses an empty one.
- `scan_line` (`:59-61`) and `scan_text` (`:64-70`) report matches with 1-based line numbers.
- Why the token list is private: publishing the ecosystem and platform words the author avoids would
  itself say what to hide (`:7-15`).

### 3.8 scripts/verify_blocklist.py (260 lines)

Defence in depth for the maintainer only: both modes need the private log, and neither is part of CI
(it does not appear in `.github/workflows/ci.yml`).

- Mode 1, coverage (`:8-12`): `table_cells(source)` (`:113-127`) parses the private log's
  `## Full Database` markdown table; `extract_candidates(source)` (`:149-155`) runs the identifier
  harvest - ALL-CAPS (`:132`), UpperCamel, lowerCamel, snake_case and finding-id shapes
  (`:133-138`) - and reports every candidate token the blocklist does not cover (`:239-256`).
- Mode 2, `--scan-repo` (`:14-20`): `scan_repo(source, allow, phrases, repo)` (`:176-208`) fails if
  any tracked file contains an identifier-shaped token from the private source (min length 3,
  `MIN_TOKEN_LEN` at `:73`) or a run of five consecutive words copied from its free text (`NGRAM`
  at `:74`, built by `ngrams(tokens, n)` (`:162-168`) with at least three non-stopwords per
  gram). Files under the published data are excluded because the build validates them
  (`:193-194`). This is the check that would have caught the 0.5.1 disclosure (`:17-20`).
- `GENERIC_ALLOWLIST` (`:44-71`) holds plain English, markdown structure and generic vulnerability
  vocabulary only; `tests/test_tools.py:155-159` pins that the domain-specific words that were
  public until 0.5.1 are gone. Optional private allowlist files carry `generic:` words and
  `phrases:` boilerplate (`:100-110`).

### 3.9 scripts/check_links.py (108 lines)

- `iter_markdown() -> list[Path]` (`:77-85`): tracked Markdown only, so private local notes are
  never read.
- `LINK_RE` (`:26`) captures `[...](...)`; web and mailto schemes are skipped (`:30`, `:53`). A
  relative target must resolve (`:61-63`). A `#fragment` on a `.md` target is checked against the
  target's headings (`:65-73`), where `headings(text)` (`:33-42`) lowercases, strips characters
  other than letters, digits, space, hyphen and underscore, and turns spaces into hyphens.

Verified: before this guide existed it reported 10 markdown files; with this guide tracked it
prints `OK: 11 markdown file(s), every relative link resolves` (`--json` reports
`markdown_files: 11, problems: []`).

### 3.10 scripts/check_markdown.py (96 lines)

- No line of a tracked `.md` may start with a mangled code fence - one backtick before an `@`
  where three belong (`:54-58`) - and every file must have an even number of fence lines
  (`:59-61`); both defects shipped in the first public release (`:5-8`).
- Every `rejection-taxonomy/tree/vX.Y.Z` link in the README must name the version in
  `pyproject.toml` (`:63-71`).
- `CITATION.cff` `version` and the newest `CHANGELOG.md` `## [x.y.z] - date` heading must agree
  with `pyproject.toml`, and `date-released` must match that heading's date (`:73-84`). This is
  the check that keeps release metadata in lockstep (Section 6).

Exit codes: 0 clean, 1 a problem, 2 cannot run (`:20`).

Verified: prints `check_markdown: fences well formed; README pin, CITATION.cff and CHANGELOG agree
with pyproject.toml`.

## 4. The test suite (tests/)

129 tests collect and pass at this commit, split: `test_build.py` 46, `test_data.py` 23,
`test_docs_numbers.py` 17, `test_hygiene.py` 14, `test_token_scan.py` 15, `test_tools.py` 14
(from `python -m pytest --collect-only -q`). The suite is what CI runs on every push; pytest
configuration is in `pyproject.toml:30-33`.

### 4.1 tests/test_data.py - the published data cannot drift

- The exact blob is pinned: `CSV_SHA256` (`tests/test_data.py:40`) is the SHA-256 of
  `data/rejections.csv` (verified at this commit), and a data change must deliberately update it in
  the same commit (`:38-40`).
- Identity: files exist (`:55-57`), digest pinned (`:60-63`), row count equals summary total
  (`:67-68`), the real data passes `validate_published` (`:71-73`) and `check_existing`
  (`:76-77`), JSON equals CSV (`:80-82`), provenance records all three private-input digests
  (`:85-89`).
- Schema: exactly the ten expected columns (`:95-96`), no forbidden column (`:99-100`), family ids
  dense from F-001 (`:103-107`), the 3 withheld rows ship exactly the five fields (`:110-115`).
- Totals: all six distributions equal `summary.json` (`:121-132`); the 0.5.x key set is a subset
  of the summary keys, because downstream readers fetch them (`:135-142`); `prehunt_catchable`
  equals its definition (`:145-147`); `public_record_preventable` equals the `public_record`
  count (`:150-152`); every `repeat_of_own = true` row is `public_record` or `own_log` - the
  0.5.1 bug (`:155-159`); the analysis split equals its definition (`:162-168`).
- Docs vs data: the README inline CSV examples must match real rows (`:174-183`); the
  `duplicate_source` and `preventable_by` tables in `SCHEMA.md` must match the summary counts
  (`:186-202`); the documented vocabulary sizes must equal the code - 19 families, 32 classes, 34
  mechanism values including sentinels, 6 outcomes, 17 gates, 20 root causes (`:205-211`) - and the
  README and SCHEMA phrasings of those sizes and of the used-value counts must hold (`:212-220`);
  `scripts/stats.py --check` must pass (`:223-227`); the README must keep stating there is no
  positive class (`:230-231`); and eight retracted phrases must never return (`:234-249`).

### 4.2 tests/test_build.py - the build, end to end, and every way it must fail

- The fixture is 14 invented rows (`tests/fixtures/classified.example.csv:1-15`), each pinning a
  derivation case; the `EXPECTED` table (`tests/test_build.py:29-44`) asserts the exact
  family_id, repeat_of_own, duplicate_source and preventable_by per row (`:73-83`), including the
  withheld row (`:86-96`), a repeat whose gate is cheaper than its own log (R-011), and a
  concurrent duplicate (R-006).
- The build must be byte-deterministic with no CRLF anywhere in the outputs (`:103-109`), publish
  provenance verbatim (`:112-113`), and `--aggregates-only` must delete per-row files even from an
  earlier build (`:116-122`).
- Refusals: eight classified-input mutations, from a value outside the vocabulary to a family root
  after its member, each fail with nothing written (`:144-161`); a missing row is legal only when
  listed as removed (`:164-168`); eight tampered published rows are caught by `--check`
  (`:171-190`), a forbidden `chain` column is caught (`:193-197`), JSON drift is caught
  (`:200-204`), missing provenance is caught (`:207-209`), an empty CSV fails (`:212-214`), and
  `--check` on a missing directory exits 2 without creating it (`:217-220`). Four malformed
  provenance objects are rejected (`:223-232`).
- The derivation rules are pinned case by case: five `duplicate_source` cases (`:238-249`) and
  eight `preventable_by` cases (`:252-266`).
- Insurance against the 0.5.1 disclosure: none of the private text-classifier table names may be
  defined in any script (`:269-276`), and the fixture copy must stay a valid build input
  (`:279-282`).

### 4.3 tests/test_docs_numbers.py - every number in the prose is pinned

`CLAIMS` (`tests/test_docs_numbers.py:42-81`) registers, per prose file, the exact phrases that
the current aggregates must produce. Then: every registered claim must actually appear (`:93-97`)
and every number-bearing phrase in the prose - a percentage, an `N of M`, a counted noun, an
`n = N` (the `NUMBER` regex at `:83-85`) - must sit inside a registered phrase (`:100-112`).
The registry must cover every prose file it applies to (`:115-117`). A number therefore cannot
be added to the docs without being registered, and a registered number cannot drift.

### 4.4 The tool tests

- `tests/test_hygiene.py` (14 tests): a BOM fails (`:27-30`), mojibake and invalid UTF-8 fail
  (`:33-39`), every private path token is caught (`:48-52`), tripwires are found with a private
  list (`:55-59`), private checks SKIP without inputs (`:62-67`), the history scan finds a token
  deleted later and one in a commit message without printing either (`:78-92`), the blocklist
  case rules hold (`:95-103`), and this repository is clean (`:106-109`).
- `tests/test_token_scan.py` (15 tests): words that contain a token pass; tokens standing alone
  fail; matching is case-insensitive; line numbers are right; the loader refuses an empty list; no
  real token list ships; and the checker and tests share one matcher (`:66-67`).
- `tests/test_tools.py` (14 tests): the query tool rejects unknown values, combines filters, and
  does not overclaim in its overview (`:23-40`); link checking covers same-file anchors (`:46-56`);
  the vocabulary cross-check agrees when titles match and fails on a retitled, missing or used
  collision id and on the old `P2` value (`:64-92`); `verify_blocklist.py` harvests lowerCamel
  and snake_case identifiers, catches identifiers and copied text across a repo, honours allowed
  phrases (`:119-152`); and the public allowlist carries no ecosystem vocabulary (`:155-159`).

## 5. CI (.github/workflows/ci.yml)

The workflow (`:1`) runs on pushes to `main` and on every pull request (`:3-6`), with a read-only
token (`:8-9`) and per-ref concurrency that cancels superseded runs (`:11-13`). Actions are pinned
to commit SHAs, with Dependabot keeping them current (`:15-17`): `actions/checkout` v7.0.1 at
`3d3c42e5aac5ba805825da76410c181273ba90b1` (`:34`) and `actions/setup-python` v7.1.0 at
`6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` (`:36`); the Python tools are pinned through the
`dev` extra, so a new ruff release cannot turn CI red on its own.

**test** (`name: test (os, python)`, `:21`) - five legs: Python 3.10, 3.11, 3.12, 3.13 on
ubuntu-latest (`:27-28`) plus a windows-latest 3.12 leg, added because a stock Windows checkout
is how the CRLF defect shipped in 0.5.1 (`:29-32`). Each leg: installs `.[dev]` (`:40-41`);
asserts the checkout is LF via `git ls-files --eol` plus a grep (`:43-48`); `ruff check .`
(`:50-51`); `pytest` (`:53-54`); `check_hygiene.py --no-history`, where the tripwire and
history scans SKIP because CI has no private inputs (`:56-60`); the link check (`:62-63`); the
markdown check (`:65-66`); `build_public_export.py --check --out data/` (`:68-69`);
`stats.py --check` (`:71-72`); and a query smoke test that also asserts that an unknown filter
value is an error (`:74-83`).

**build** (`:85-111`) - the full build on the synthetic fixture, in both modes: build then
`--check` the result (`:96-102`), and `--aggregates-only` asserting that no per-row file exists
in the output (`:103-111`).

**vocabulary** (`:113-135`) - reads the pinned tag (`:125-127`), checks out
`KhomDev/viability-gate` at exactly that tag with no persisted credentials (`:128-133`), and runs
`check_vocabulary.py --viability-gate _viability-gate --require` (`:134-135`).

On a pull request, the five test legs report under names of the form `test (ubuntu-latest, 3.12)`
and `test (windows-latest, 3.12)` per the `name:` template at `:21`, alongside `build` and
`vocabulary`; merging requires them all green.

## 6. Release and versioning process

- Versioning policy (`CHANGELOG.md:7-10`): a schema change - a column or vocabulary value added,
  removed or renamed - is a breaking change and gets a major version; a change to which rows hold
  which values is a data release and gets a minor version. `CHANGELOG.md` follows Keep a Changelog
  and SemVer (`:3-5`).
- The current release is `[0.6.0] - 2026-11-06` (`CHANGELOG.md:14`), and four artifacts must agree
  on it, enforced by `scripts/check_markdown.py:63-84`: `pyproject.toml:3` (`0.6.0`),
  `CITATION.cff:17` (`version: "0.6.0"`), the newest `CHANGELOG.md` heading (`:14`), and the
  README tag link `rejection-taxonomy/tree/v0.6.0` (`README.md:379`). `CITATION.cff:18` carries
  `date-released: 2026-11-06`, which must equal the CHANGELOG heading's date.
- A commit that changes published numbers must say which numbers changed and why, and update
  `CSV_SHA256` in `tests/test_data.py` (`CONTRIBUTING.md:51-54`).
- `data/provenance.json` digests the private source, classifier and ledger each release was built
  from, so the author can rebuild byte-for-byte; nobody else can, by design (`README.md:323-325`).
- Releases 0.3.0 through 0.5.1 no longer have tags: the repository history was reset twice to remove
  published classifier rules and identifying material (`CHANGELOG.md:124-127`, `:236-239`, and
  the 0.6.0 Security section `:23-38`). The 0.6.0 changelog also documents the
  derived-column fixes with the row ids that moved (`:74-87`).
- Takedown rows leave `removed_ids` in the next release so ids are not reused and the sequence does
  not silently close up (`SECURITY.md:29-33`; empty at this release, `data/provenance.json:5`).

## 7. Known limitations

Recorded in `README.md:196-227`, restated here with their references; read them before quoting any
number:

1. **No positive class.** The dataset is a log of rejections; no paid finding exists in it, so no
   success rate, precision or base rate can be produced (`README.md:201-202`).
2. **`earliest_gate` is self-assessed.** It is the author's post-hoc judgement, not a record of what
   any tool said; a different analyst would assign some rows differently (`README.md:203-205`).
3. **"Earliest gate" is not "preventable".** `preventable_by` is the column that answers whether a
   rejection could have been avoided; most checks also need the finding in hand
   (`README.md:206-211`).
4. **Repeated families.** Rows are not independent; the effective sample is the 98 distinct families,
   and cells with one or two rows are anecdotes (`README.md:212-214`).
5. **The rules that cite this dataset were derived from it.** Calibration against them is in-sample
   (`README.md:215-217`).
6. **One researcher, one selection process.** No comparison group exists (`README.md:218-220`).
7. **Self-assessed labels throughout.** `bug_family`, `root_cause_class`, `duplicate_source` and
   `preventable_by` are classifications by the author of the reports (`README.md:221-222`).
8. **`unknown` and `other` are populated, and reported**, not guessed away (`README.md:223-224`).
9. **Rule drift.** A verdict reflects the rules in force at submission time, not today's
   (`README.md:225-226`).
10. **`below_payout_floor` rows are heavily redacted.** See the disclosure model
    (`README.md:227`, and `:273-285` for what ships).

`docs/method.md:45-72` states the same constraint from the analysis side: distributions and a
reusable taxonomy are supported; inference about a specific program, field-wide statistics, base
rates and cross-chain comparisons are not.

## 8. How this guide was verified

At commit `4212b246e562f48c10814495e13737366ac5d8a5`, with a clean working tree on branch `main`,
every CI job's local equivalent passed before this document was written, and the full suite passed
again with the document present:

    python -m pip install ".[dev]"
    git ls-files --eol                # no CRLF or mixed working-tree endings
    python -m ruff check .
    python -m pytest                   # 129 passed
    python scripts/check_hygiene.py --no-history
    python scripts/check_links.py
    python scripts/check_markdown.py
    python scripts/build_public_export.py --check --out data/
    python scripts/stats.py --check
    python scripts/query.py            # plus the smoke filters of ci.yml:74-83
    python scripts/build_public_export.py --classified tests/fixtures/classified.example.csv
        --provenance tests/fixtures/provenance.example.json --out <tmp>    # then --check, then --aggregates-only
    python scripts/check_vocabulary.py --print-pinned-tag
    git clone --depth 1 --branch v0.5.0 https://github.com/KhomDev/viability-gate.git <tmp-vg>
    python scripts/check_vocabulary.py --viability-gate <tmp-vg> --require

Counts in this guide were computed from `data/rejections.csv` directly and cross-checked against
`data/summary.json`; line references were checked file by file, mechanically, against every file the
guide cites; behavior claims were verified by running the named script. Anything a future release changes will move one of the referenced lines -
re-check against the commit in the header before relying on a reference.

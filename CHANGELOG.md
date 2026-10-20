# Changelog

All notable changes to this repository. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The published dataset is a derived artifact. A schema change is a breaking change
for anyone consuming `data/`, so it gets a major version.

## [Unreleased]

## [0.4.0] - 2026-10-20

A data release: **+14 rejections, now 111 rows** (was 97). No schema change, so a
minor version - every column, vocabulary and withholding rule is unchanged, and
the export validates against the same allowlist.

### Added

- **14 newly triaged smart-contract rejections** classified onto the existing
  closed vocabularies (no new `bug_family` or `mechanism_class` was invented to
  fit a row). After bucketing the batch is 9 `duplicate`, 4 `informational` and
  1 `intentional_design`.
- `other_mechanism` is **no longer empty**: 4 rows landed in the residue class,
  exactly as the schema said could happen. This is visible in `summary.json`
  rather than hidden by forcing a closer-but-wrong class.

### Changed

- Regenerated `data/summary.json` and the README generated block from the
  enlarged `data/rejections.csv`. Headline shifts: effective n 82 -> 96 distinct
  families; pre-hunt-gate catchable 71/97 (73.2%) -> 80/111 (72.1%); duplicate
  share 37.1% -> 40.5%; the broad "analysis did not hold up" split 33.0% -> 33.3%.
- Narrative row counts in `README.md` and `data/SCHEMA.md` updated from 97 to 111
  (and the derived per-bucket counts) to match the regenerated aggregates.

## [0.3.0] - 2026-10-14

The first tagged release in this repository. It also contains the history-reset
fix below. The dataset and its schema are unchanged.

### Fixed

- **Eight code-fence lines in `README.md` were `` `@ `` instead of three
  backticks**, so four blocks (the CSV sample, two shell blocks and the BibTeX
  citation) rendered as plain text on GitHub.
- **The README told readers to pin `v0.2.0`**, a tag that does not exist after
  the history reset. The pin is now `v0.3.0`.
- **GitHub could not identify the licence.** `LICENSE` carried the data-licence
  section after the MIT text, which defeats licence detection. `LICENSE` is now
  the MIT text alone; the CC BY 4.0 data-licence section moved, unchanged, to
  `LICENSE-DATA`.

### Added

- **`scripts/check_markdown.py`**, run in CI: fails on a `` `@ `` fence line, on
  an odd number of fences in any tracked Markdown file, and when the tag the
  README pins differs from the version in `pyproject.toml`.
- **Dependabot** for pip and GitHub Actions, grouped.

### Changed

- CI actions moved to `actions/checkout@v7` and `actions/setup-python@v7`; the
  v4/v5 majors target Node 20, which the runners no longer support natively.
- `CITATION.cff` now carries `version`, and `date-released` is this release.

## Repository history reset - 2026-10-10

Repository history was reset on 2026-10-10 to remove identifying material from
earlier commits; earlier versions are no longer available.

The tree itself is unchanged except for the tripwire fix recorded below.

### Fixed

- **The identity-token matcher used the wrong boundary.** It compared the
  character either side of a hit against a set that treated `-`, `_` and `.` as
  separators, so an ordinary English word that merely contained a token was
  reported as that token. The matcher is now a word boundary, the per-file
  allowlist it needed is gone, and `tests/test_token_scan.py` pins both
  directions: words that contain a token pass, and every declared token fails.
- The file walk now uses `git ls-files`, so the gitignored private redaction
  blocklist is not reported as a leak by the author's own local run.

## 0.2.0 - 2026-10-10 (untagged; predates the history reset)

### Breaking

- **`mechanism` (free text) is replaced by `mechanism_class` (closed
  vocabulary of 31 classes).** The old column was authored prose validated
  against a denylist. A denylist cannot catch a paraphrase, so the hole was
  structural. Every published value is now drawn from a vocabulary and validated
  by **allowlist**: a value outside the vocabulary is a build failure.
- **The `paid` column is removed.** It was constant (`no` in all 97 rows) and
  implied a positive class that does not exist. The dataset contains rejections
  only; that is now stated as a limitation instead of carried as a column.
- **The gate id `P2_duplicate_check` is renamed to `D1_duplicate_check`.** In
  [viability-gate](https://github.com/KhomDev/viability-gate), `P2` means
  "privileged-role-gated". One token meaning two things across two repositories
  was a documentation bug. The rename is applied to the data, the schema, the
  query tool, the tests and the docs.
- **Four columns added:** `family_id`, `repeat_of_own`, `duplicate_source`,
  `preventable_by`.
- **`below_payout_floor` rows are now heavily redacted.** They ship only
  `bug_family`, `triage_class`, `earliest_gate`, `root_cause_class` and
  `mechanism_class = withheld_valid`. The other four fields are the literal
  value `withheld`.

### Added

- `scripts/stats.py` computes every aggregate into `data/summary.json` and
  rewrites the generated block in the README. `--check` fails if either is
  stale, and the test suite runs it.
- `effective_n`: the number of distinct `family_id`s (82), reported alongside
  the 97 rows.
- Two explicit definitions of the "did the analysis hold up" split, because the
  published 16.5%/84% framing was not a definition. Strict (spam only) is 1;
  broad (spam + informational + intentional design) is 32 of 97.
- A `preventable_by` split replacing the "73% preventable before reading a line
  of code" claim, which counted a concurrent duplicate that nobody can pre-hunt.
- `scripts/query.py` filters for the new columns.
- `SECURITY.md`, `CONTRIBUTING.md`, this changelog, and issue templates for
  corrections and takedown requests.

### Fixed

- Mojibake (mis-decoded dashes and accents) removed from every tracked file, and a check added
  that fails on those byte sequences.
- Orphaned table rows after the blocklist paragraph, and a duplicated
  "Finding IDs" row.
- The "only 4% were about impact being wrong" sentence, which contradicted the
  repository's own table. Replaced with the two definitions above.

### Known limitations

Unchanged and restated: no positive class, one researcher, four months,
self-assessed gate assignments, in-sample rule derivation, and an `unknown`
bucket in `duplicate_source` (12 rows) and `preventable_by` (15 rows) that is
reported rather than guessed away.

## 0.1.0 - 2026-10-08 (untagged; predates the history reset)

### Added

- Initial release: 97 logged rejections, classified by triage outcome and
  earliest catchable gate.

[Unreleased]: https://github.com/KhomDev/rejection-taxonomy/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/KhomDev/rejection-taxonomy/releases/tag/v0.4.0
[0.3.0]: https://github.com/KhomDev/rejection-taxonomy/releases/tag/v0.3.0

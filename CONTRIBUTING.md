# Contributing

Corrections are the most valuable contribution to this repository.

## The two things that help most

### 1. A correction to a classification

Every row is a judgement made by one person. If a row's `triage_class`,
`earliest_gate`, `root_cause_class`, `duplicate_source` or
`preventable_by` is wrong, open a
[correction issue](.github/ISSUE_TEMPLATE/correction.md) and say which row and
why. Cite the program's own wording where you can.

Because the dataset is generated, a correction is applied to
`scripts/build_public_export.py` and the data is rebuilt. **Never open a PR that
hand-edits `data/`** - it will be rejected, because the next build would
overwrite it.

### 2. A new mechanism class, or a fix to the vocabulary

`mechanism_class` is a closed vocabulary. If a row does not fit any class, that
is a bug in the vocabulary. Open an issue naming the class you would add and what
it would cover; the bar is that it describes a *shape* of bug rather than one
instance.

## What will not be accepted

- **Any change that adds a target dimension.** No protocol, chain, ecosystem,
  language, date or severity column, under any name. The `--check` mode fails if
  one reappears, and CI runs it.
- **Any change that adds free text to the published data.** The allowlist is the
  design.
- **Any de-anonymisation attempt**, including "just tell me which program row
  N is". That is the one thing this dataset exists not to do.

## Working on the code

```bash
python -m pytest tests/ -q
python scripts/build_public_export.py --check --out data/
python scripts/stats.py --check
```

The first two need no private input. `build_public_export.py` regenerates
`data/` only if you supply the private source and blocklist, which are not in this
repository and will not be.

## Commit messages

Conventional commits (`fix:`, `feat:`, `docs:`, `test:`, `chore:`). A commit
that changes published numbers should say which numbers changed and why.

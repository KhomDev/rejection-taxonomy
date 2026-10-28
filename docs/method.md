# Method

How the 113 rows were classified, what the classification can and cannot support, and why the
dataset is shaped the way it is.

---

## What a row is

One row = one submission to one public bug-bounty program that was **not paid**.

The private source is a working database maintained across four months of hunting. Each entry
records the protocol, the report title, the triage verdict, the triage reasoning, and a post-hoc
analysis of the root cause and the gate that should have caught it.

The public export reduces each row to four categorical values and an id. Everything else is
dropped, including the protocol.

## The three classification axes

### `triage_class` — what the program decided

Bucketed by the **first matching rule** in a fixed order. The order is load-bearing:

| Order | Value | Rationale |
|---:|---|---|
| 1 | `below_payout_floor` | Checked first because these are the highest-value rows. A row can read "out of scope for *X* payout" and be semantically a payout-floor outcome, not a scope one. |
| 2 | `spam` | Fabricated impact contradicted by the report's own PoC. |
| 3 | `duplicate` | A real finding, already reported or known. |
| 4 | `out_of_scope` | Scope boundary or exclusion clause. |
| 5 | `informational` | Valid observation, no security impact. |
| 6 | `intentional_design` | Fallback. Absorbs `Held` and `Not applicable`. |

**Known lossiness.** `Held` (unresolved) folds into `intentional_design` (by design). Those are
different things. The fold exists to keep one source of truth with the canonical private stats
script; `held` is not a distinct public value. Three rows are affected.

### `earliest_gate` — what would have caught it

The gate token must appear at the **start** of the private cell. This mirrors the canonical script's
regex, so a cell beginning with a gate token buckets to that gate, and a cell beginning with
anything else becomes `REALISM` or `UNCLASSIFIED`.

This is the most useful column and the least objective one — see below.

### `root_cause_class` — why it failed

A closed vocabulary of ~20 values. The private column is free text and routinely contains other
researchers' handles and upstream finding IDs, so it is never passed through raw. Anything the
mapping does not recognise becomes `other`.

## What this dataset can support

✅ **Distributions.** How often each outcome occurs, and which gates would have caught what.
✅ **A taxonomy to reuse.** The gate list and the outcome list are the transferable part.
✅ **A prior on where effort is wasted.** Scope, duplication and economics dominate; impact
analysis is a minority.

## What it cannot support

❌ **Any inference about a specific program.** There is no target axis by design.
❌ **Statistical claims about the field.** n=113, one researcher, four months, one selection process.
❌ **Claims about base rates.** This is a log of *failures*. It says nothing about how many
submissions succeeded, so it cannot yield a success rate.
❌ **Comparisons across chains or languages.** Those columns do not exist here.

## Sources of bias, stated plainly

1. **Selection bias.** These are programs I chose to hunt. My target-selection habits — including
   the bad ones — are baked into every proportion.
2. **Self-assessed gates.** The `earliest_gate` value is my own post-hoc judgement of what would
   have caught the finding. It is not a record of what any tool said at the time. A different
   analyst would assign some rows differently.
3. **Survivorship in reverse.** I logged rejections. A researcher who logged only rejections will
   always see a dataset that looks like failure.
4. **Rule drift.** Programs change rules. A verdict reflects the rules in force at submission time,
   not today's.
5. **Small n per cell.** Several `earliest_gate` values have 1–2 rows. Those cells are anecdotes,
   not rates.

## The privacy model

The dataset carries **no target dimension**: no protocol, chain, ecosystem, date or severity.

An earlier draft published `chain` and `ecosystem`, on the theory that withholding the protocol
name was sufficient. It is not. With 113 rows across a few dozen targets, chain + ecosystem +
outcome + gate is a **join key** — a fingerprint, not an anonymisation. The columns were removed
and the `--check` mode now fails if they reappear.

Two mechanisms enforce this:

1. **Closed vocabularies (primary).** Every published value must be a member of `VALID_TRIAGE`,
   `VALID_GATES` or `VALID_ROOT_CAUSE`. Source text is never passed through, so no private token
   can reach the output by construction.
2. **Blocklist (defence in depth).** `scripts/verify_blocklist.py` scans the private source for
   capitalised tokens and reports anything the blocklist does not cover, in case the architecture
   is later changed.

`scripts/build_public_export.py` fails closed: if any blocked token survives into the output, it
writes nothing and exits non-zero.

## Reproducing

```bash
python scripts/build_public_export.py \
    --source /path/to/private/_REJECTION_DATABASE.md \
    --blocklist redaction-blocklist.PRIVATE.yaml \
    --out data/

python scripts/build_public_export.py --check --out data/
python scripts/verify_blocklist.py \
    --source /path/to/private/_REJECTION_DATABASE.md \
    --blocklist redaction-blocklist.PRIVATE.yaml
```

`--aggregates-only` publishes only the summary tables and drops the per-row tuples. Every headline
number is unchanged.

**Never hand-edit `data/`.** The published totals are generated and are verified against the
canonical private stats script, so they cannot drift from the source of truth.

# Representativeness and replication

What this log is a sample of, what it cannot be a sample of, and the protocol an
independent researcher would follow to replicate it. [README Known limitations](../README.md#known-limitations)
lists the caveats; this page turns them into an argument, states which claims the
data refuses to make, and pre-registers what would count as a replication.

**Status at v0.6.1:** no external replication exists. This page is the protocol, not
a result.

## 1. The sampling frame

A row enters the dataset only if all four of these held:

1. the finding was submitted to a public bug-bounty program;
2. it was closed without payment;
3. the author wrote it into the private submission log;
4. the row was publishable after the withholding rule - 3 rows are withheld and
   ship five categorical fields only.

Paid findings are excluded by construction: there is no positive class. Unlogged
submissions are invisible: the log is a working record, not a census. So the
113 logged rejections are not a random sample of submissions, not a random sample
of the author's own output, and not a sample of the field. They are the subset of
one researcher's rejected work that survived steps 3 and 4.

The frame has a hard boundary: every row is conditional on being rejected. No
denominator of attempts or targets is published, so even the author's own rejection
rate cannot be computed from this repository. Nothing here is a rate of anything
except a share within a failure set.

The three withheld rows matter for the frame too. They are the confirmed-valid
rejections - a real bug, a working proof, a team that agreed, a reward table that
could not pay. They are counted in every aggregate, but they take no family id and
ship five fields only, so family-level counts are smaller than row counts for that
reason as well as for repeats.

## 2. Target selection

These are the programs the author chose to hunt. The choice was not random and is
not published by design: the dataset has no target, chain, ecosystem, language or
date dimension. What can be said is structural rather than empirical:

- Selection followed expected value, accessibility and familiarity. Those correlate
  with which bugs were found, and therefore with which triage outcomes appear.
- A hunter who spent the same period on two deep targets instead of many shallow
  ones would not face the same duplicate risk per submission, and would likely see
  a different duplicate share.
- The duplicate signal here comes from known issues, prior audits, public
  disclosures, the author's own log and one concurrent submission. A contest
  duplicate - shared but paid - is not a category this dataset can contain,
  because there is no positive class.
- There is no comparison group: no paid rows, no other researcher's rows, and no
  record of the submissions that were never made.

The consequence is not that the proportions are wrong. They are correct for this
log. It is that they are conditional on a target-selection process that a reader
cannot inspect, and that a different process can plausibly reverse the ordering of
the smaller buckets.

## 3. One researcher

One person selected the targets, wrote the reports, read the triage responses,
assigned every category, invented the vocabularies and chose the gate list. Every
label is a single coder's judgement, with no second coder and no published
inter-rater agreement. Reliability is a property of classification events that
happen in private, so it cannot be measured from the published data.

Two biases follow directly:

- **Confirmation.** The taxonomy was built from these rows, so the rows will fit it.
  Agreement between the data and the taxonomy is partly definitional.
- **Consistency pressure.** A single coder tends to apply their own categories the
  same way, which reads as reliability in the aggregate and can hide a systematic
  misreading that a second coder would catch.

What the published data can offer instead is auditability of consistency: every
value is closed-vocabulary, the derivation rules are public and tested, and a
reader can recompute every count. None of that establishes validity. Only an
independent coder on an independent sample does.

## 4. No positive class, and what it rules out

Every row was rejected. That rules out, by construction, every quantity that needs
a denominator of attempts or a comparison against a paid finding:

- an acceptance rate, a success rate, a base rate, or an expected value;
- the precision or recall of any gate on *submitted* findings, because there is no
  positive set to measure false stops against;
- any claim that a check would have saved a submission, beyond the author's
  post-hoc counterfactual recorded in `preventable_by`;
- any comparison between "findings worth reporting" and "findings rejected", since
  the first set is absent.

The most tempting wrong reading is the headline:

> 63 of 113 (55.8%) could have been stopped from the public record.

That is a share **of rejections**, conditional on rejection. It is not the precision
of those checks. The same checks might also have stopped paid findings, and this
dataset cannot see that, because the paid findings are not in it. If a check
catches 55.8% of failures and also catches a large share of successes, it is a
false-stop machine, and no number here detects that. The check-level false-stop
rate is the single most important measurement this dataset cannot make; section 9
of this document makes it a replication deliverable for a log that has a paid set.

The same caution applies to 78 rows (69.0%), whose earliest gate is D1 or G1-G5.
That is a distribution of post-hoc gate assignments, not an out-of-sample catch
rate for the tool that implements the gates.

## 5. Effective n and repeated families

Rows are not independent observations. The totals and their limits:

- 113 rows, 110 of which publish a family; the effective n is
  98 distinct bug families.
- 12 rows repeat a family the author had already submitted. Together with the first
  submissions, that is 21 rows in 9 families; the largest has 4 rows.
- The repeat count is a lower bound. A family whose first submission predates the
  log cannot be detected, and neither can a family the author simply forgot to log.

So the honest sample size for anything family-level is at most 98, not 113, and it
could be lower if the author split one bug into two families. At mechanism level it
is lower again: 31 of the 32 mechanism classes are used, 7 of them by a single row,
and 91 of 113 rows are the only row with their combination of bug family, mechanism
class, triage outcome, earliest gate and root cause. Cells with one or two rows are
anecdotes and must be read as such. The defensible claims are about the large
buckets, and the ordering of the large buckets is what a replication should test.

## 6. In-sample rule derivation

The gate list, the outcome buckets and the mechanism vocabulary were derived by
reading these same rows. The `earliest_gate` column is the author's post-hoc
judgement of what would have caught the finding, assigned after the rejection was
known. Agreement between the taxonomy and the data is therefore closer to a ceiling
than to an unbiased estimate: the categories were chosen to describe the rows, so
finding that the rows fit the categories is not evidence that either generalises.

This is why the dataset is useful as a **taxonomy to reuse and a prior to test**,
and not as a validation of itself. The only way to find out whether the ordering
survives outside this log is to apply the same instrument, unchanged, to rows the
author never saw - which is what section 9 specifies.

## 7. Identifiability limits

The disclosure model strips the target axis and all free text, but it is an
argument, not a proof. 91 of 113 rows are the only row with their five-value
category tuple, and 7 mechanism classes hold a single row. A reader who already
knows a specific submission - its program and roughly what it claimed - could
recognise its row.

That constrains replication. A replicator who publishes their own target list, and
joins it to these categorical tuples, can re-identify rows of this log. The
protocol below therefore publishes only the same kind of categorical export, and
never a row-level merge.

## 8. What the dataset can and cannot support

| Claim | Supported? | Why |
|---|---|---|
| The distribution of triage outcomes in this log | Yes | Computed, tested, stable within the log |
| A reusable gate and mechanism taxonomy | Yes | It is the transferable artifact |
| Hypotheses about where effort is wasted before submission | Yes | As hypotheses, ordered by bucket size |
| Proportions within the rejection set | Yes, conditioned on this frame | Every row is a rejection from this selection process |
| Any success, acceptance or base rate | No | No positive class |
| Precision, recall or false-stop rate of any gate | No | Needs paid findings |
| Comparison across chains, ecosystems, languages or programs | No | Those columns do not exist |
| Statistical claims about the bug-bounty field | No | n = 113, one researcher, one selection process |
| That a listed check would have saved the submission | No | `preventable_by` is a post-hoc counterfactual |

## 9. Pre-registered external replication protocol

The point of a replication is not to confirm these proportions. It is to measure
whether the instrument and the ordering survive a different sampling frame, and to
supply the two things this log cannot: a second coder and a positive class.

### 9.1 What to hold fixed

- **The unit.** One submission to one public program that was closed without
  payment, entered exactly once. Paid findings are recorded separately and never
  merged into the rejection rows.
- **The schema at this tag.** Use `data/SCHEMA.md` at v0.6.1 verbatim: ten columns,
  the closed vocabularies in `scripts/vocab.py`, the withholding rule for
  confirmed-valid rows, and the first-match ordering rules for `triage_class` and
  `earliest_gate`.
- **The arithmetic.** Use `scripts/stats.py` unchanged, so a difference between the
  two datasets is a difference in coding or frame, not in aggregation.
- **The derivation rules.** `family_id`, `repeat_of_own`, `duplicate_source` and
  `preventable_by` are computed by `scripts/build_public_export.py` from classified
  values only. Reuse them rather than re-deriving by hand.
- **The checks.** The public build's invariants and `--check` modes are part of the
  protocol, not optional.

The replicator may add a vocabulary value only by opening an issue first and
reporting how many rows needed it. An instrument that needs new categories for a
large share of rows is not the same instrument, and that is a finding, not a
failure.

### 9.2 What to record before looking at the comparison

- the replicator's sampling frame: ecosystem, program count, date range,
  target-selection rule, number of submissions, and what counts as "logged";
- whether paid findings were also logged, and if so how many;
- whether coding was done blind to this repository or after reading it - both are
  informative, but they answer different questions;
- the pre-declared thresholds below, committed to a public repository and hashed
  (or archived with a DOI) before the comparison is run. Deviations are reported.

Pre-registration here means the thresholds and the comparison are fixed before the
replication's numbers are seen. It does not require the replicator to hide their
own data from themselves.

### 9.3 What to measure

1. **Coding agreement.** Code the replicator's rows against this vocabulary and
   report per-column agreement between two independent coders on the replication
   side. Target: Cohen's kappa of at least 0.6 on `triage_class` and
   `earliest_gate`, pre-declared. Below that, the instrument is not reproducible
   and the comparison stops there.
2. **Top-bucket ordering.** Report whether duplicates are the largest triage bucket
   and whether D1 is the modal earliest gate. Pre-declare how large a margin the
   second bucket needs before the ordering counts as reversed.
3. **Distribution comparison.** Compare the rejection-conditional distributions of
   triage and gate with a pre-declared interval or effect size. Do not decide
   "similar" after seeing the numbers.
4. **Gate-assignment stability.** The gap between the two coders' `earliest_gate`
   assignments is the honest error bar this log cannot supply. Report it for the
   largest buckets.
5. **False stops, if paid rows exist.** The share of paid findings that the
   candidate checks would have stopped, using the same gate definitions. This is
   the precision number the rejection-only log refuses to invent. Report it
   separately from every rejection-conditional share.

### 9.4 How to pool, and when to refuse

- **Refuse pooled proportions by default.** The two sampling frames are not
  exchangeable, and pooling a duplicate share or a preventable share produces a
  mixture with unknown weights. Report the datasets side by side, each with its own
  denominator.
- **Pool only a pre-registered cross-frame estimand,** such as the share of
  rejections that were duplicates, and only with a heterogeneity statement. If the
  two shares disagree by more than the pre-declared interval, the result is
  "the framing does not transfer", not an average.
- **Never pool a rejection set with a paid set** to synthesise a success rate. The
  selection into each set is different and unknown.
- **Never merge rows.** Publish a second categorical export with its own
  provenance; do not join it to this one, because 91 of 113 rows are uniquely
  identifying tuples and the join can re-identify targets.
- **Report provenance and version** for both datasets, including the tag and the
  commit. A replication against a moving branch is not a replication.

### 9.5 What a completed replication would look like here

A replication that follows this protocol would produce a second dataset, its own
provenance file, and a short report with the five measurements above. If it is
published, it should be linked from this page and from the README, and this page's
status line should change from "protocol, not a result" to a citation of it. No
part of this protocol depends on the author of this log being involved.

## 10. What evidence would change the conclusions

The conclusions this dataset actually makes are narrow: the taxonomy is usable, the
large buckets are duplicates, scope and economics, and the derivation rules are
public. Here is what would overturn them.

- **Top buckets reverse in a different frame.** If a replicator's log has a
  different largest bucket - for example if informational or out-of-scope findings
  dominate and duplicates do not - then the ordering is local to this
  target-selection process, and the practical advice derived from it is local too.
- **The gate share does not survive a second coder.** If independent coders assign
  `earliest_gate` differently on a shared sample, the earliest-gate distribution is
  a coding artifact, and every "the six gates would have caught" reading of it
  collapses.
- **The same checks stop a large share of paid findings.** If a paid-findings
  dataset shows the candidate checks killing a material share of successes, then
  the 63 of 113 (55.8%) figure describes failures only and must never be presented
  as the yield of a filter. This is the finding that would most change the
  practical recommendations.
- **The vocabulary does not cover independent rows.** If a replication needs new
  mechanism or gate categories for a pre-declared large share of its rows, the
  taxonomy is a description of this log rather than a reusable instrument.
- **The derived columns cannot be reproduced.** If a replicator cannot reproduce
  `duplicate_source` or `preventable_by` from the documented rules, the public
  build is under-specified and the published values are not independently checkable.
- **Selection is shown to explain the patterns.** Evidence that the duplicate and
  scope shares track the target-selection process rather than the work - for
  example, contest logs where duplicates are paid - would move the explanation from
  "where effort is wasted" to "which programs this author chose".

What would **not** change the conclusions: a larger version of this same log, a
re-coded copy from the same researcher and the same selection process, or an
argument that the numbers are small without measuring an alternative. Those change
the precision of a local estimate, not its frame.

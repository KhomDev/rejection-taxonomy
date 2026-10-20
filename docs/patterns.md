# What the data says

Six patterns that recur across 111 logged rejections. Each one is something you can check for on
your next submission, and each is backed by rows you can pull with `scripts/query.py`.

---

## 1. Duplication is the largest single outcome, and it is not about your skill

**43 of 111 rejections (38.7%) were duplicates.**

This is the most demoralising category and the least discussed. It does not mean you missed a bug.
It means you found a *real* one that someone else found first, or that the team already knew about.

```bash
python scripts/query.py --triage duplicate
```

The mechanisms in that list are frequently interesting — unbacked credit minted on a trade path,
nested-hook gas desynchronisation, reward dilution. The outcome was still zero.

**What to do differently.** Enumerate the known-issue families and the prior-audit surface *before*
hunting. Not the table of contents — the actual findings. A prior audit naming a file is not the
same as covering your function.

**Twelve rows repeat a family already in this dataset**, across nine families (the largest has four
rows). The original article said two. Some of those are duplicates of your own earlier, unlogged
submission — `R-092` is one — and an unlogged outcome is invisible to your own duplicate check. Log
every submission, including the rejected ones, or you will re-file against yourself.

`repeat_of_own` and `family_id` in the data are what make this visible:

```bash
python scripts/query.py --repeats -v
```

---

## 2. "Valid but unpaid" is a real category, and it is the most expensive one

**3 rows (2.7%) were confirmed valid and paid nothing**, because the program's reward table had no
tier at that severity.

```bash
python scripts/query.py --triage below_payout_floor -v
```

That is a small share of the total and a large share of the cost. In each case the work was done
correctly: a real bug, a working proof, a team that agreed it was real. The structure of the
program made it worth zero.

**What to do differently.** Read the reward table first. Identify the lowest severity with a
non-zero reward, and ask whether your thesis can reach it. If the program is Critical-only and your
mechanism is a Medium-class value misallocation, stop — not "hunt carefully", stop.

Note that two of these three rows are classified `out_of_scope` in the private record because the
program's own wording put them there. The *semantic* outcome is a payout-floor miss, which is why
this dataset buckets them separately.

---

## 3. The analysis was wrong far less often than the targeting was

Two honest definitions, because the published "4%" framing was not one:

- **strict** - the impact was fabricated: **1 row**.
- **broad** - no security impact, intentional design, or fabricated: **39 of 111 (35.1%)**.

The old framing used the `informational` bucket alone (16.5%) as the numerator and called the
remaining 83.5% "targeting". That is 100% minus one bucket, and it counts intentional-design rows as
targeting failures when they are analysis failures.

The direction still holds, and it is the useful part: scope, duplication and economics dominate. The
instinct on entering this field is that the bottleneck is finding harder bugs. It is not. It is
knowing which bugs are worth finding.

```bash
python scripts/query.py --family reentrancy        # 2 rows
python scripts/query.py --family accounting        # 13 rows
```

The exotic categories are thin. The mundane ones — value counted wrong, input trusted when it
should not be — dominate.

---

## 4. Privileged-role preconditions are the biggest single exclusion trap

Within the 26 `out_of_scope` rejections, privileged-role clauses were the largest sub-cause.

```bash
python scripts/query.py --root-cause oos_privileged_role -v
```

Almost every program excludes "attacks requiring access to privileged addresses". The trap is that
this reads broader than it is. Two genuinely different findings get filed under it:

- The attack **requires an admin to act maliciously** → out of scope, correctly.
- A **reasonable admin action has a non-obvious destructive second-order effect** → potentially in
  scope. The admin is not misbehaving; the code is.

Check which one you have before abandoning the finding.

---

## 5. Panic-and-revert is not an impact

**Five rows** are `panic`-family findings, and they were closed informational, out of scope, or
SPAM. A transaction that reverts rolls back every state change: the persisted state is byte-identical
to the pre-call state, and the caller has only burned their own gas.

```bash
python scripts/query.py --family panic -v
```

The clearest case is `R-015`: the headline claimed a *permanent fund lock*, the proof demonstrated a
transaction abort, and the result was SPAM — the worst outcome in the dataset, worse than
informational, because the report fabricated an impact its own evidence disproved.

**What to do differently.** Ask what state exists *after* the revert that did not exist before. If
the answer is nothing, you have a robustness note, not a vulnerability. And never let a title claim
more than the proof shows.

---

## 6. Async ordering and cross-boundary state are where the subtle bugs live

`async_ordering` accounts for **7 rows** and is one of the most consistent sources of genuinely
interesting mechanisms: state committed in a compute phase before an action-phase settlement, an
a failed delivery notification, a nonce that advances in a path a later revert rolls back.

```bash
python scripts/query.py --family async_ordering -v
```

These are also the ones most likely to be closed as duplicates or design decisions, because the
protocol has usually thought about its own message flow. They are worth hunting and worth
pre-checking hard.

---

## The gate summary

| Gate | Rows | Runnable before reading code? |
|---|---:|---|
| Duplicate / known-family check | 41 | ✅ |
| Exclusion-clause transcription | 20 | ✅ |
| Intentional design / no-impact review | 13 | ⚠️ needs the finding |
| Prior-audit sweep | 7 | ✅ |
| No-attacker-win analysis | 12 | ⚠️ needs the finding |
| Payout-tier check | 5 | ✅ |
| Out-of-scope file tree | 4 | ✅ |
| Realism gates | 3 | ⚠️ needs the finding |
| Below severity floor | 2 | ✅ |
| Test-suite intention grep | 1 | ✅ |
| Program ceiling | 1 | ✅ |
| Cooperating-party exit | 1 | ⚠️ needs the finding |
| Headline-vs-evidence mismatch | 1 | ⚠️ needs the finding |

**78 of 111 (70.3%) were catchable by a gate you can run before opening an editor.**

```bash
python scripts/query.py --prehunt --json | jq -r '.[].mechanism'
```

---

## Reading this honestly

- **n = 111, one researcher, four months.** These are proportions in a personal log, not base rates.
- **This is a log of failures.** It says nothing about how many submissions succeeded, so no success
  rate can be derived from it.
- **The gate assignments are self-assessed.** They are the most useful column and the least objective.
- **Selection bias is baked in.** These are the programs I chose to hunt, with my own habits —
  including the bad ones — shaping every number.

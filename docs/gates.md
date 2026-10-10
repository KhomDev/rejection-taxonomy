# The six pre-hunt gates

Each gate is a question you can answer **before reading a line of code**. Together they account
for 71 of 97 logged rejections (73.2%) in this dataset.

They are ordered by cost: gate 1 is a single web page, gate 6 needs a git log. Run them in order
and stop at the first failure.

---

## Gate 1 — Severity floor

**Question:** Is there a payout tier at the severity I can plausibly reach?

**Why it matters:** the single most expensive outcome is a *confirmed valid* finding that pays
nothing because the reward table has no row for its severity. Three rows in this dataset are
exactly that.

**How to run it:**

1. Open the program's live rewards page.
2. Find the reward table. Record every severity row.
3. Note the **lowest severity with a non-zero reward** — that is the floor.
4. Ask: can my thesis plausibly reach that severity?

If the answer is no, **stop**. Not "hunt carefully" — stop. A Medium-class mechanism on a
Critical-only program has an expected value of zero.

**Failure mode this prevents:** `below_payout_floor` — 3 rows (3.1%), the most expensive category
per row in the dataset.

See the [tier-shape taxonomy](https://github.com/KhomDev/bounty-economics) for the closed set of
shapes a reward table resolves to.

---

## Gate 2 — Exclusion clauses

**Question:** Does a written exclusion clause cover my bug class?

**Why it matters:** this is the second-largest category at 20 rows (20.6%). The clauses are
usually on the same page as the reward table, and they are cheap to transcribe.

**How to run it:**

1. Copy every out-of-scope clause from the program's scope page, **verbatim**.
2. Classify each one against the [clause-class taxonomy](https://github.com/KhomDev/bounty-economics).
3. For each, ask whether your intended bug class falls inside it.
4. Turn the clause into a regex over your finding description and test it.

**The highest-yield sub-case:** `privileged_role` and `human_error` clauses. These read broader
than they are. A finding that *requires* an admin to act maliciously is out of scope — but a
finding where a **reasonable admin action has a non-obvious destructive second-order effect** can
be in scope. The admin is not misbehaving; the code is. Check that distinction before abandoning a
finding.

**Failure mode this prevents:** `oos_exclusion_clause` and `oos_privileged_role` — 20 rows.

---

## Gate 3 — Scope tree

**Question:** Is the root cause inside the scoped files?

**How to run it:**

1. Get the exact in-scope file list (often "only files under `sources/`").
2. Trace your finding's **root cause** to a file — not the impact site, the root cause.
3. If the root cause is outside the tree, the finding is out of scope regardless of impact.

**The trap:** a real bug with a real impact whose root cause lives in a deployment script, a test
utility, or an off-chain component. Those are outside `sources/` and will be closed as out of
scope. 4 rows in this dataset.

**Failure mode this prevents:** `oos_scope_boundary` — 4 rows.

---

## Gate 4 — Prior audits

**Question:** Is this surface already closed?

**How to run it:**

1. Collect every linked audit report, contest result and disclosure.
2. Note which **files and functions** each one covers — not the titles.
3. Record the program's **known issues** section verbatim.
4. Note the **post-audit delta**: what changed after the last audit.

**Two traps:**

- **A prior audit naming a file is not the same as covering your function.** Read the finding.
- **The post-audit delta is the richest surface** — and also where you are least likely to be
  duplicating. A large rewrite after the last audit is where new bugs live.

**Failure mode this prevents:** `prior_audit_known` — 7 rows.

---

## Gate 5 — Test-suite intent

**Question:** Does the project's own test suite assert that this behaviour is intended?

**How to run it:**

1. Grep the target's test suite for the behaviour you are about to report.
2. Look for tests that **assert the current behaviour is correct**.
3. A test asserting the behaviour is a strong signal it is by design.

**The trap:** a test asserting the behaviour does not always mean it is intended — sometimes the
test encodes the bug. But it raises the bar substantially: you now have to argue the test itself is
wrong.

**Failure mode this prevents:** `intentional_design` via assertion — 1 row directly, but this gate
also feeds the 15-row intentional-design category.

---

## Gate 6 — Fork novelty

**Question:** Is this a fork whose behaviour is documented upstream?

**How to run it:**

1. Identify whether the target is a fork (compare against known upstreams).
2. If it is, check whether the behaviour you found exists identically upstream.
3. If it does and upstream documents it as intended, the finding is a documented design decision.

**The trap:** verbatim forks inherit both bugs and *documented* design decisions. A finding that is
novel in the fork but documented upstream is not a finding.

---

## Gates that are not pre-hunt

The remaining 26 rows in this dataset were catchable only with the finding in hand. They fall into
two groups:

**Report-level anti-patterns** — run before submitting, not before hunting. The full catalogue is
in [viability-gate](https://github.com/KhomDev/viability-gate): no attacker-win, headline-vs-evidence
mismatch, cooperating-party exit, defective PoC, and others.

**Realism gates** — attacker-model, realistic-configuration, and concession checks. These are the
post-mortem additions: they catch findings that are mechanically real but unreachable under the
deployed configuration, or that contradict their own stated preconditions.

---

## Using the gates

The gates are a **prioritiser, not a kill-switch**. Two cautions:

- **A first-pass triage decision is not a final verdict.** A finding that looks out of scope on a
  first read may be in scope on a second — particularly around the privileged-role distinction.
- **Over-filtering is its own failure mode.** If the gates kill everything, you have calibrated
  them too aggressively and will miss real findings.

Run them in order, record what each one said, and when a gate fails, write down *why* before moving
on. The `earliest_gate` column in this dataset is exactly that record.

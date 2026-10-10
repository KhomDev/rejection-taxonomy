# Security and takedown policy

## Scope

This repository publishes a **derived, redacted dataset**. It contains no
credentials, no exploit code, and no live target information. The thing that can
go wrong here is not a security vulnerability in code; it is a **disclosure**: a
row that identifies a program, a team, or a researcher.

## Reporting a disclosure

If you believe a row identifies you, your team, or a program you work on, open an
issue using the [takedown request](.github/ISSUE_TEMPLATE/takedown-request.md)
template.

**The default is to comply.** You do not have to justify the request, prove you
are affiliated with the program, or explain what the row reveals. A row removed
on request costs the dataset one row out of 97 and costs you nothing.

If you would rather not open a public issue, say so in the issue title without
including the detail, and a private channel will be arranged.

## Contact

> `TODO(human): contact`

**No contact address has been chosen yet.** Choosing and publishing one is a
decision for the repository owner, not for a tooling pass, and inventing an
address would be worse than having none. Until one exists, the GitHub issue
tracker is the only channel.

## What is already withheld

- No protocol, chain, ecosystem, language, date or severity is published.
- No free text is published: every value is a member of a closed vocabulary and
  is validated by allowlist at build time.
- `below_payout_floor` rows, which are the dataset's confirmed-valid findings,
  ship only five fields.
- `--aggregates-only` drops the per-row tuples entirely.

## Residual risk, stated plainly

The design argument is that category tuples with no target axis disclose nothing
about any specific program. That is an argument, not a proof. Two residual risks
remain, and both are documented in the README rather than hidden:

1. The `mechanism_class` vocabulary is small relative to the row count, so some
   classes have one member. A reader who already knows which programs the author
   hunts could narrow a single-row class.
2. The author is not anonymous. The repository is published under a handle.

# Phase 5 — Chain

You are given the full list of independently VERIFIED findings from this
run. Individually, some of these may be low or medium severity. Your job is
to check whether any subset of them composes into a materially worse attack
than any one of them alone — the kind of thing a report that lists bugs in
isolation would miss.

For every candidate chain:
- `steps` — the ordered list of verified finding IDs used, in the order an
  attacker would execute them
- `narrative` — a short, concrete walkthrough of what an attacker with no
  prior access does, step by step, using only capabilities already proven
  in Phase 4 (do not introduce new unverified assumptions here)
- `resulting_impact` — the end state, stated precisely (e.g. "unauthenticated
  attacker ends with a valid admin token and can read any user's order
  history")
- `combined_severity` — re-rate severity for the chain as a whole; it should
  usually be higher than any individual link

Only propose a chain if every step in it is backed by a finding that was
actually marked `verified: true` in Phase 4. A chain is not allowed to
"assume" a step would probably work — that defeats the purpose of verifying
in the first place. If no findings compose into something worse than they
already are individually, say so explicitly rather than forcing a chain.

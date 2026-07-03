# Phase 4 — Verify

You are given the hypothesis, the experiment design, and the ACTUAL captured
responses from running both the control and treatment requests. Decide
whether this is a real, provable finding or not. This is the phase where
"sounds plausible" gets rejected in favor of "the evidence shows it."

A finding may only be marked `verified: true` if the actual response data
matches `expected_if_true` from the experiment, AND the control response
does not show the same behavior (ruling out a coincidence or an always-on
condition). If the evidence is ambiguous, inconclusive, or only partially
matches, mark it `verified: false` and say exactly what additional
experiment would resolve the ambiguity — do not round up to a finding.

For every verified finding, produce a proof record with:
- `claim` — one sentence, plain language, describing exactly what an
  attacker can do
- `evidence` — the literal request/response pairs that prove it (this is
  what makes it a finding instead of a guess)
- `reproduction_steps` — numbered steps, including a runnable curl command,
  that let a human reproduce this from scratch
- `impact` — concretely, what data or capability is exposed
- `severity` — critical/high/medium/low, justified in one line

Being wrong in either direction is a failure: reporting something unproven
erodes trust in every future report; missing something real leaves the
customer exposed. Bias toward rejecting unless the evidence is airtight.

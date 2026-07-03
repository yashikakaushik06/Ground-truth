Ground truth — a 5-phase LLM agent for finding & proving web vulnerabilities
it's a small,
opinionated pipeline where each phase is a separate, carefully-scoped prompt,
the model's own claims are checked against real HTTP evidence it just
collected, and an eval harness scores the whole thing against known ground
truth so "the agent said it found something" and "the agent actually found
something" are two different, both-measured things.


## Architecture

```
target_app/     a small, self-contained, intentionally-vulnerable API
                 (same category as OWASP Juice Shop / DVWA — used only
                 against itself, never a third party)
agent/
  prompts/       one markdown file per phase — the actual prompt engineering
  llm_client.py  real Anthropic client, or an honestly-labeled offline
                 mock reasoner when no API key is present (see below)
  tools.py       the one tool the agent gets: a sandboxed HTTP request,
                 hard-restricted to the configured target host
  pipeline.py    orchestrates the 5-phase loop
evals/
  ground_truth.json   the planted vulns + one deliberate red herring
  run_eval.py          runs the agent, scores recall/precision/evidence
  results/             output of the last real run (committed, not staged)
docs/
  juice_shop_target.md how to extend the same pipeline to OWASP Juice Shop
                        for a larger, harder eval suite
```

## The loop, mirrored phase-for-phase

| Phase | Prompt | What it's not allowed to do |
|---|---|---|
| **Understand** | `agent/prompts/understand.md` | Guess at vulnerabilities — only build a model of intended behavior |
| **Assume** | `agent/prompts/hypothesize.md` | Propose generic vuln classes — every hypothesis names a specific mechanism and a falsifiable signal |
| **Experiment** | `agent/prompts/experiment.md` | Test without a control — every experiment has a control + treatment request |
| **Verify** | `agent/prompts/verify.md` | Round up ambiguous evidence to a finding — bias is to reject unless airtight |
| **Chain** | `agent/prompts/chain.md` | Assume an unverified step would "probably work" — chains can only use already-verified findings |

## Why there's a mock mode (and why that's the honest choice)

I don't have an Anthropic API key yet. Rather than hand you a repo that
only *claims* to work, `agent/llm_client.py` has two paths:

- **Live**: set `ANTHROPIC_API_KEY`, every phase call goes to Claude with
  the corresponding prompt file as the system prompt.
- **Mock**: no key set, a small rule-based reasoner (`MockReasoner` in the
  same file) plays the same role, so the *orchestration, the tool-use loop,
  and the eval scoring* — the actual engineering — can be verified end to
  end today. Every mock output is tagged `"mode": "mock"` in the JSON so
  it's never mistaken for a live result.

Swapping to live is a one-line change (see `.env.example`). I built it this
way on purpose: an eval harness you can't run without paying for API calls
isn't a real eval harness, it's a promise.

## Real results from an actual run (mock mode, committed in `evals/results/`)

```
$ python3 evals/run_eval.py
{
  "mode": "mock",
  "ground_truth_total": 4,
  "verified_count": 4,
  "true_positives_matched": ["V1", "V2", "V3", "V4"],
  "recall": 1.0,
  "precision": 1.0,
  "false_positives": 0,
  "red_herring_incorrectly_verified": false,
  "evidence_complete_rate": 1.0,
  "chains_found": 1,
  "run_time_seconds": 0.03
}
```

All 4 planted vulnerabilities (SQL injection, IDOR, mass assignment /
privilege escalation, secrets disclosure) were found **and** verified with
real request/response evidence against the running target — not asserted
from a prompt. The one deliberate red herring (`/api/export`, which looks
like path traversal but is actually allow-listed) was correctly **not**
reported, which is the number I actually care about most: a tool that
reports everything it's suspicious of isn't useful to a human triaging
results.

The chain phase composed the three individually-serious bugs into the
attack an actual attacker would run:

> Unauthenticated attacker authenticates via SQL injection → escalates to
> admin via mass assignment → uses admin standing to read every customer's
> order history via IDOR.

Full evidence (literal request/response pairs, curl-reproducible) is in
`evals/results/findings.json`.


## What I'd build next with more time / a real key

- A live run against Claude, with the mock reasoner's rule-based verdicts
  used as a regression baseline to catch prompt regressions
  ("did phase 4 get *more* permissive after I edited the prompt?")
- Point the same pipeline at OWASP Juice Shop for a much larger, harder eval
  (see `docs/juice_shop_target.md`) — the toy target here is intentionally
  small so ground truth stays unambiguous, but it doesn't stress-test the
  Understand phase the way 100+ inconsistent routes would.
- A Phase 0 (discovery/crawl) so the agent builds its own endpoint list
  instead of being handed one, which is closer to the real problem.
- Cost/latency tracking per phase, since "reliable, repeatable steps" in
  production also means "affordable at scale."


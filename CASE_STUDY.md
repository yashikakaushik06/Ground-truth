# Case study: building a 5-phase vulnerability-hunting agent

## The problem, as I read it

The job description draws a specific loop — understand, assume, experiment,
verify, chain — and says explicitly that the work is "core product work,
not prompt tweaking on the side." I took that as the actual brief: don't
write one clever jailbreak-y prompt that gets a model to output something
that looks like a pentest report. Build the thing that makes an LLM's
output trustworthy enough to act on, which is a systems problem as much as
a prompting one.

So I built a small pipeline (`vuln-hunter`) against a target I own
(`vuln-mart`, a deliberately vulnerable toy API), with an eval harness that
scores it against ground truth I wrote myself. Everything in this repo
actually runs; the numbers in the README are from a real execution, not a
description of intended behavior.

## Design decision 1: separate the phases into separate prompts

It would be faster to write one big prompt: "here's an API, find bugs and
prove them." I didn't do that, for the same reason the job posting doesn't
describe the role that way either. A single prompt collapses "I have a
hunch" and "I have proof" into the same output, which is exactly the
"sounds smart" failure mode the posting calls out. Splitting Hypothesize
from Verify means the model has to commit to a falsifiable claim *before*
it sees the evidence, and a separate pass has to look at real HTTP
responses and decide, in writing, whether the evidence actually matches
what was predicted. That structural separation is doing more work than any
individual sentence of prompt wording.

## Design decision 2: every experiment needs a control, not just a payload

Early on I drafted the Experiment prompt to just ask for "a request that
would prove this." That's how you get false positives — a request that
returns something unusual might be unusual for reasons that have nothing to
do with the hypothesis (rate limiting, a flaky endpoint, a coincidental
500). I rewrote the prompt to require a control request and a stated
`expected_if_false`, not just `expected_if_true`. Verify then has to check
that the control *didn't* show the same signal. This is the single change
that would matter most against a real, messier target than my toy app,
where noise is much more common than in a 5-endpoint sandbox.

## Design decision 3: a red herring in the ground truth, on purpose

`ground_truth.json` isn't just a list of the real bugs — it includes one
endpoint (`/api/export`) that looks exploitable (a `format` query param,
which screams "path traversal" if you're pattern-matching) but is actually
safe because it's allow-listed. If I only scored recall, a system that
reports everything even remotely suspicious would score perfectly and be
useless to a human triaging its output. Precision — and specifically,
whether the red herring gets correctly rejected — is the number that
actually tells you if "verify" is doing real work or just formatting the
hypothesis as if it were confirmed.

## Design decision 4: an honest offline mode instead of a fake demo

I don't have an Anthropic API key yet. I could have written the README to
describe what the pipeline "would do" with a real model, but that's asking
you to trust a claim I can't back up. Instead, `agent/llm_client.py` has a
real path (`ANTHROPIC_API_KEY` set → actual Claude calls with the prompt
files as system prompts) and a mock path (a small rule-based reasoner) that
implements the *same interface* so the orchestration, the tool-calling
loop, and — critically — the eval scoring logic are all exercised for
real, today, and the results in this README are real output from a real
run, just not from a frontier model's reasoning. Every mock response is
tagged `"mode": "mock"` in its own output so there's no ambiguity about
what produced it. Switching to live is one environment variable.

I think this is the more defensible engineering choice, not a workaround:
an eval harness that can't be run and inspected by the person reading it is
just a claim with extra steps. If I get the key, the exact same
`run_eval.py` becomes a live benchmark of the real model's actual reasoning
against my prompts, which is the artifact I'd actually want if I got this
job.

## What the mock mode can't tell you (and I'm not pretending it can)

The mock reasoner's rules were hand-written by me, specifically for
`vuln-mart`'s four planted bugs. It will not generalize to a target it
wasn't written for — that's expected and fine, because its job isn't to be
a good vulnerability hunter, it's to be a faithful stand-in for "some
system responds to phase prompts" so the *plumbing* around it is verifiably
correct. The interesting, hard part of this job — whether a real model's
Hypothesize output is actually sharp against an app it's never seen, whether
Verify is appropriately skeptical against ambiguous real-world evidence —
is exactly the part that needs a live key and a harder target (see
`docs/juice_shop_target.md`) to actually answer. I didn't want to paper
over that gap; I wanted to build the harness that would let someone
measure it honestly on day one.

## What I'd change with more runway

- Right now `Understand` is handed a hardcoded endpoint list. A real
  version needs a discovery phase — crawling, reading an OpenAPI spec if
  one exists, or probing common patterns — before it can claim to
  "understand how an app is meant to work" from scratch.
- The eval only measures the final report. A harder eval would also score
  the intermediate hypotheses themselves — did Hypothesize name the right
  mechanism even when Verify correctly rejected a badly-designed
  experiment for it? That's a finer-grained signal than pass/fail on the
  end-to-end pipeline and would catch regressions earlier in the loop.
- Cost and latency per phase, tracked per run, because "turn messy model
  behavior into reliable, repeatable steps" implies a production constraint,
  not just a correctness one — a pipeline that's 100% precise but costs $40
  and 20 minutes per endpoint doesn't ship.

## Why I built it this way instead of a flashier demo

It would have been easy to write a single prompt, point it at a known-CVE
app, and paste an impressive-looking report into a README. I didn't want to
submit something whose only proof is that it reads well. Everything
claimed in this repo — the recall/precision numbers, the red-herring
rejection, the attack chain — is reproducible with `python3
evals/run_eval.py` in under a second, against code you can read in full.
That's the standard I'd want to hold my own work to on this team.

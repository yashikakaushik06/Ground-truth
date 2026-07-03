# Extending the eval suite to OWASP Juice Shop

`vuln-mart` (this repo's `target_app/`) is deliberately small so the ground
truth is unambiguous and the eval score is trustworthy. The natural next
step — and the reason the agent's `endpoints` list and `HttpTool.base_url`
are both just config, not hardcoded — is pointing the same five-phase loop
at [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/), the
industry-standard intentionally-vulnerable practice application, which ships
its own scoreboard of ~100 documented challenges to score against instead
of a hand-written `ground_truth.json`.

## Why this is a good second target

- It's built for exactly this purpose: legal, safe, designed to be attacked.
- It's far larger and messier than `vuln-mart`, which stresses the
  **Understand** phase much harder — a toy app with 5 endpoints doesn't
  test whether the agent can build a correct mental model of 100+ routes
  with inconsistent naming and nested resources.
- It has a public difficulty rating per challenge, so the eval can report
  not just recall/precision but a **recall-by-difficulty** breakdown —
  closer to what "the system actually catches bugs, not just sounds smart"
  means at a harder tier.

## How to wire it in

1. Run Juice Shop locally (never against someone else's hosted instance
   without permission):
   ```bash
   docker run -d -p 3000:3000 bkimminich/juice-shop
   ```
2. Replace the hardcoded `ENDPOINTS` list in `agent/pipeline.py` with a
   real discovery step — Juice Shop exposes its OpenAPI-ish route surface,
   or the agent can be given a crawl tool as Phase 0 (not implemented here,
   noted as the obvious next increment).
3. Pull Juice Shop's own challenge list (`/api/Challenges/`) as the ground
   truth instead of a hand-written JSON file, and adapt `evals/run_eval.py`
   to match a verified finding against a challenge by its `key` field
   instead of by endpoint substring.
4. Run `TARGET_URL=http://127.0.0.1:3000 python3 evals/run_eval.py`.

This is intentionally left as a documented extension rather than pre-built,
because doing it properly needs a real LLM key (the mock reasoner's rules
are hand-written for `vuln-mart`'s specific bugs and won't generalize) and
because the scoring logic against Juice Shop's own challenge feed deserves
its own small design pass rather than being bolted on.

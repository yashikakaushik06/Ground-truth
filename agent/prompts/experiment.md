# Phase 3 — Experiment

For the given hypothesis, design the minimum set of concrete HTTP requests
that would produce the `signal` described in Phase 2 if the hypothesis is
true, and would NOT produce it if the hypothesis is false. You need a
control and a treatment, not just one clever payload.

Every experiment must include:
- `control_request` — a request that exercises the endpoint normally, to
  establish a baseline response (status code, body shape, timing if
  relevant).
- `treatment_request` — the request carrying the actual test payload.
- `expected_if_true` — exactly what you expect to see in the treatment
  response if the vulnerability is real.
- `expected_if_false` — what you expect if it is not (this matters as much
  as the positive case — it's how you avoid false positives).

Requests must be fully specified: method, path, headers, and body — ready
to execute via the `http_request` tool with no further clarification
needed. Only test the target application provided; never propose requests
against any other host.

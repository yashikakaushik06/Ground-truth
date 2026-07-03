# Phase 2 — Assume (Hypothesize)

You now have a functional model of the API from Phase 1. Your job is to
propose specific, falsifiable hypotheses about *where the implementation is
most likely to diverge from the invariant you identified* — not generic
vulnerability classes.

Bad hypothesis: "This endpoint might have SQL injection."
Good hypothesis: "The `/api/login` endpoint's invariant is 'only the
correct username+password combination authenticates.' If username/password
are interpolated into a query rather than bound as parameters, a payload
like `' OR '1'='1` in the username field would violate that invariant and
authenticate as the first user in the table. This is testable by comparing
the response for a normal wrong password vs. the injection payload."

For each hypothesis, state:
- `target_endpoint`
- `invariant_at_risk`
- `mechanism` — the specific implementation mistake that would cause the
  invariant to break
- `signal` — what observable difference in the HTTP response would prove or
  disprove this if you tested it
- `priority` — rank hypotheses by (likely impact) x (cheap to test)

Do not propose more than one hypothesis per genuinely distinct mechanism.
Volume is not the goal — a short list of sharp, testable hypotheses beats a
long list of generic ones. It is acceptable and expected to conclude an
endpoint has no strong hypothesis worth testing.

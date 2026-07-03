"""
LLMClient — a thin abstraction so the pipeline doesn't care whether it's
talking to a real model or the offline mock.

If ANTHROPIC_API_KEY is set, every call goes to the real Claude API using
the phase prompt as the system prompt. If it isn't set, MockReasoner is
used instead: a small, honestly-labeled rule engine that plays the same
role so the *pipeline and eval harness* can be demoed and tested end-to-end
without burning API credits or requiring a key. Every mock response is
tagged "mode": "mock" so nobody could mistake it for a live model result.

Swapping to live is a one-line change: export ANTHROPIC_API_KEY=...
"""
import json
import os
import re


class LLMClient:
    def __init__(self, model="claude-sonnet-4-6"):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.live = bool(self.api_key)
        if self.live:
            import anthropic  # only imported when actually needed
            self._client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self._mock = MockReasoner()

    def call(self, phase, system_prompt, user_payload):
        """
        phase: one of understand/hypothesize/experiment/verify/chain
        system_prompt: the contents of agent/prompts/<phase>.md
        user_payload: dict, JSON-serializable context for this call
        returns: parsed dict/list from the model's JSON response
        """
        if self.live:
            return self._call_live(system_prompt, user_payload)
        return self._mock.respond(phase, user_payload)

    def _call_live(self, system_prompt, user_payload):
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system_prompt + "\n\nRespond with ONLY valid JSON, no prose, no markdown fences.",
            messages=[{"role": "user", "content": json.dumps(user_payload)}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        text = re.sub(r"^```json|```$", "", text.strip(), flags=re.MULTILINE).strip()
        return json.loads(text)


class MockReasoner:
    """
    Deterministic, rule-based stand-in for the LLM. Not trying to be
    "smart" — trying to be an honest, inspectable placeholder that proves
    the pipeline/eval plumbing works before a real model is wired in.
    """

    def respond(self, phase, payload):
        fn = getattr(self, f"_{phase}", None)
        if fn is None:
            raise ValueError(f"mock has no handler for phase {phase}")
        result = fn(payload)
        return {"mode": "mock", "result": result}

    # ---- Phase 1: Understand ------------------------------------------------
    def _understand(self, payload):
        out = []
        for ep in payload["endpoints"]:
            path = ep["path"]
            invariant = "no strong invariant identified"
            actors = "any"
            if "login" in path:
                invariant = "only correct username+password should authenticate"
                actors = "anonymous"
            elif re.search(r"orders/<", path) or "orders/" in path:
                invariant = "a user should only ever be able to read their own orders"
                actors = "authenticated owner"
            elif "profile" in path:
                invariant = "a user should only be able to modify their own non-privileged fields (never role)"
                actors = "authenticated self"
            elif "internal" in path or "config" in path or "debug" in path:
                invariant = "internal/debug data must never be reachable without admin auth"
                actors = "admin only"
            out.append({
                "endpoint": path,
                "purpose": ep.get("description", ""),
                "actors": actors,
                "trust_boundary": "client-supplied fields should not be trusted for authz decisions",
                "invariant": invariant,
            })
        return out

    # ---- Phase 2: Hypothesize -----------------------------------------------
    def _hypothesize(self, payload):
        hyps = []
        for ep in payload["understanding"]:
            path = ep["endpoint"]
            if "login" in path:
                hyps.append({
                    "target_endpoint": path,
                    "invariant_at_risk": ep["invariant"],
                    "mechanism": "credentials may be string-interpolated into a SQL query instead of parameter-bound",
                    "signal": "an injection payload in username authenticates without a valid password",
                    "priority": 1,
                })
            elif "orders" in path:
                hyps.append({
                    "target_endpoint": path,
                    "invariant_at_risk": ep["invariant"],
                    "mechanism": "endpoint may fetch by id with no ownership check against the caller's token",
                    "signal": "requesting an order id not owned by the authenticated user still returns its data",
                    "priority": 1,
                })
            elif "profile" in path:
                hyps.append({
                    "target_endpoint": path,
                    "invariant_at_risk": ep["invariant"],
                    "mechanism": "update handler may apply every client-supplied field blindly, including role",
                    "signal": "sending role=admin in the update body results in the account's role becoming admin",
                    "priority": 1,
                })
            elif "internal" in path or "config" in path:
                hyps.append({
                    "target_endpoint": path,
                    "invariant_at_risk": ep["invariant"],
                    "mechanism": "endpoint may have been left unauthenticated after debug use",
                    "signal": "an unauthenticated GET returns secret/config data",
                    "priority": 2,
                })
            elif "export" in path:
                hyps.append({
                    "target_endpoint": path,
                    "invariant_at_risk": "format parameter should not allow reading arbitrary server files",
                    "mechanism": "possible unsanitized format/path parameter",
                    "signal": "supplying a path traversal style value in format changes behavior or errors informatively",
                    "priority": 3,
                })
        return hyps

    # ---- Phase 3: Experiment -------------------------------------------------
    def _experiment(self, payload):
        h = payload["hypothesis"]
        path = h["target_endpoint"]
        if "login" in path:
            return {
                "control_request": {"method": "POST", "path": "/api/login",
                                     "body": {"username": "alice", "password": "wrongpassword"}},
                "treatment_request": {"method": "POST", "path": "/api/login",
                                       "body": {"username": "admin' -- ", "password": "anything"}},
                "expected_if_true": "treatment returns 200 with a token/role, control returns 401",
                "expected_if_false": "both requests return 401",
            }
        if "orders" in path:
            return {
                "control_request": {"method": "GET", "path": "/api/orders/101",
                                     "headers": {"Authorization": "Bearer tok-alice-001"}},
                "treatment_request": {"method": "GET", "path": "/api/orders/103",
                                       "headers": {"Authorization": "Bearer tok-alice-001"}},
                "expected_if_true": "treatment (alice's token, bob's order 103) still returns 200 with bob's order data",
                "expected_if_false": "treatment returns 403/404",
            }
        if "profile" in path:
            return {
                "control_request": {"method": "POST", "path": "/api/profile/update",
                                     "headers": {"Authorization": "Bearer tok-alice-001"},
                                     "body": {"username": "alice"}},
                "treatment_request": {"method": "POST", "path": "/api/profile/update",
                                       "headers": {"Authorization": "Bearer tok-alice-001"},
                                       "body": {"role": "admin"}},
                "expected_if_true": "treatment response shows role: admin for alice's account",
                "expected_if_false": "treatment response still shows role: user",
            }
        if "internal" in path or "config" in path:
            return {
                "control_request": {"method": "GET", "path": "/api/health"},
                "treatment_request": {"method": "GET", "path": "/api/internal/config"},
                "expected_if_true": "treatment returns 200 with secret_key/debug fields, no auth required",
                "expected_if_false": "treatment returns 401/403/404",
            }
        return {
            "control_request": {"method": "GET", "path": "/api/export?format=csv"},
            "treatment_request": {"method": "GET", "path": "/api/export?format=../../etc/passwd"},
            "expected_if_true": "treatment leaks file contents or a stack trace revealing the filesystem",
            "expected_if_false": "treatment returns a clean 400 'unsupported format' error",
        }

    # ---- Phase 4: Verify -------------------------------------------------
    def _verify(self, payload):
        h = payload["hypothesis"]
        control = payload["control_response"]
        treatment = payload["treatment_response"]
        path = h["target_endpoint"]

        def base(verified, claim, impact="", severity="low"):
            return {
                "target_endpoint": path,
                "verified": verified,
                "claim": claim,
                "evidence": {"control": control, "treatment": treatment},
                "impact": impact,
                "severity": severity,
            }

        if "login" in path:
            ok = treatment.get("status") == 200 and control.get("status") != 200
            return base(ok,
                        "SQL injection in /api/login allows authentication bypass without valid credentials.",
                        "full account takeover of the first matching user via crafted username", "critical")
        if "orders" in path:
            ok = (treatment.get("status") == 200
                  and treatment.get("body", {}).get("owner_id") not in (None, 1))
            return base(ok,
                        "IDOR on /api/orders/<id>: authenticated users can read any other user's order by id.",
                        "disclosure of other customers' order contents and totals", "high")
        if "profile" in path:
            ok = treatment.get("body", {}).get("role") == "admin"
            return base(ok,
                        "Mass assignment on /api/profile/update allows self-escalation to admin via the role field.",
                        "any authenticated user can grant themselves admin privileges", "critical")
        if "internal" in path or "config" in path:
            ok = treatment.get("status") == 200 and "secret_key" in treatment.get("body", {})
            return base(ok,
                        "Unauthenticated /api/internal/config discloses the application secret key.",
                        "secret key exposure enables downstream token/session forgery", "medium")
        # RH1 export — expected to NOT verify
        ok = False
        return base(ok, "Export format parameter did not yield file disclosure; input is allow-listed.",
                     "", "low")

    # ---- Phase 5: Chain -------------------------------------------------
    def _chain(self, payload):
        findings = {f["target_endpoint"]: f for f in payload["verified_findings"]}
        chains = []
        profile = next((f for f in payload["verified_findings"] if "profile" in f["target_endpoint"]), None)
        orders = next((f for f in payload["verified_findings"] if "orders" in f["target_endpoint"]), None)
        login = next((f for f in payload["verified_findings"] if "login" in f["target_endpoint"]), None)
        if login and profile and orders:
            chains.append({
                "steps": ["login-sqli", "profile-mass-assignment", "orders-idor"],
                "narrative": (
                    "1) Attacker with no account authenticates via SQL injection on /api/login. "
                    "2) Using the returned token, attacker calls /api/profile/update with role=admin, "
                    "self-escalating to admin. 3) Attacker enumerates /api/orders/<id> to read every "
                    "customer's order history and totals, now with an authoritative admin token."
                ),
                "resulting_impact": "unauthenticated attacker ends with admin privileges and full read access to all customer order data",
                "combined_severity": "critical",
            })
        elif profile and orders:
            chains.append({
                "steps": ["profile-mass-assignment", "orders-idor"],
                "narrative": (
                    "1) Any authenticated low-privilege user escalates to admin via the mass-assignment bug. "
                    "2) With admin standing, the same IDOR is used to enumerate every customer's orders."
                ),
                "resulting_impact": "low-privilege account escalates to admin and reads all order data",
                "combined_severity": "critical",
            })
        return chains

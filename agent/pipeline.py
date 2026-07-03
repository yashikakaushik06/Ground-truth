import json
import os
from pathlib import Path

from agent.llm_client import LLMClient
from agent.tools import HttpTool

PROMPTS_DIR = Path(__file__).parent / "prompts"

ENDPOINTS = [
    {"path": "/api/login", "method": "POST", "description": "authenticate a user with username/password"},
    {"path": "/api/orders/<id>", "method": "GET", "description": "fetch a single order by id, requires auth token"},
    {"path": "/api/profile/update", "method": "POST", "description": "update the caller's own profile fields"},
    {"path": "/api/internal/config", "method": "GET", "description": "internal/debug configuration endpoint"},
    {"path": "/api/export", "method": "GET", "description": "export data in a given format"},
]


def load_prompt(name):
    return (PROMPTS_DIR / f"{name}.md").read_text()


class SecurityResearchAgent:
    def __init__(self, base_url):
        self.llm = LLMClient()
        self.http = HttpTool(base_url)
        self.base_url = base_url
        self.log = []

    def _run_phase(self, phase, payload):
        prompt = load_prompt(phase)
        result = self.llm.call(phase, prompt, payload)
        self.log.append({"phase": phase, "input": payload, "output": result})
        return result["result"] if isinstance(result, dict) and "result" in result else result

    def run(self):
        # Phase 1: Understand
        understanding = self._run_phase("understand", {"endpoints": ENDPOINTS})

        # Phase 2: Hypothesize
        hypotheses = self._run_phase("hypothesize", {"understanding": understanding})

        # Phase 3 + 4: Experiment then Verify, per hypothesis
        verified_findings = []
        all_attempts = []
        for h in hypotheses:
            experiment = self._run_phase("experiment", {"hypothesis": h})
            control_resp = self.http.request(experiment["control_request"])
            treatment_resp = self.http.request(experiment["treatment_request"])
            verdict = self._run_phase("verify", {
                "hypothesis": h,
                "experiment": experiment,
                "control_response": control_resp,
                "treatment_response": treatment_resp,
            })
            all_attempts.append(verdict)
            if verdict.get("verified"):
                verified_findings.append(verdict)

        # Phase 5: Chain
        chains = self._run_phase("chain", {"verified_findings": verified_findings})

        return {
            "target": self.base_url,
            "mode": "mock" if not self.llm.live else "live",
            "understanding": understanding,
            "hypotheses_tested": len(hypotheses),
            "all_attempts": all_attempts,
            "verified_findings": verified_findings,
            "chains": chains,
        }


def run_and_save(base_url, out_path):
    agent = SecurityResearchAgent(base_url)
    report = agent.run()
    Path(out_path).write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    base_url = os.environ.get("TARGET_URL", "http://127.0.0.1:5001")
    out = os.environ.get("OUT", "evals/results/findings.json")
    report = run_and_save(base_url, out)
    print(f"Findings: {len(report['verified_findings'])} verified, "
          f"{len(report['chains'])} chain(s), mode={report['mode']}")

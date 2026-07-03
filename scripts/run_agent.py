"""CLI entry point: python scripts/run_agent.py [target_url] [out_path]"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent.pipeline import run_and_save

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5001"
    out = sys.argv[2] if len(sys.argv) > 2 else "evals/results/findings.json"
    report = run_and_save(target, out)
    print(f"Findings: {len(report['verified_findings'])} verified, {len(report['chains'])} chain(s)")

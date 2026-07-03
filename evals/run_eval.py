"""
Eval harness — this is the part of the job description that matters most:
"Build evals that measure whether the system actually catches bugs, not
just sounds smart."

Runs the agent end-to-end against the target, then scores its findings.json
against evals/ground_truth.json:
  - recall: of the real planted vulns, how many did it verify?
  - precision: of everything it verified, how much was actually real?
  - false positive check: did it verify the red herring?
  - evidence quality: does every verified finding carry reproducible proof?
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agent.pipeline import run_and_save


def endpoint_matches(reported_endpoint, gt_endpoint):
    # normalize "/api/orders/<id>" vs "/api/orders/103" style differences
    r = reported_endpoint.split("?")[0].rstrip("/")
    g = gt_endpoint.replace("<id>", "").rstrip("/")
    return g.split("<")[0] in r or r in g


def score(report, ground_truth):
    gt_vulns = ground_truth["vulnerabilities"]
    gt_herrings = {rh["endpoint"] for rh in ground_truth["red_herrings"]}
    verified = report["verified_findings"]

    matched_gt_ids = set()
    for f in verified:
        for gt in gt_vulns:
            if endpoint_matches(f["target_endpoint"], gt["endpoint"]):
                matched_gt_ids.add(gt["id"])

    false_positives = [
        f for f in verified
        if not any(endpoint_matches(f["target_endpoint"], gt["endpoint"]) for gt in gt_vulns)
    ]
    herring_reported_as_real = [
        f for f in verified
        if any(endpoint_matches(f["target_endpoint"], h) for h in gt_herrings)
    ]

    recall = len(matched_gt_ids) / len(gt_vulns) if gt_vulns else 0
    precision = (len(verified) - len(false_positives)) / len(verified) if verified else 0

    evidence_complete = sum(
        1 for f in verified
        if f.get("evidence", {}).get("control") and f.get("evidence", {}).get("treatment")
    )

    return {
        "mode": report["mode"],
        "ground_truth_total": len(gt_vulns),
        "verified_count": len(verified),
        "true_positives_matched": sorted(matched_gt_ids),
        "recall": round(recall, 2),
        "precision": round(precision, 2),
        "false_positives": len(false_positives),
        "red_herring_incorrectly_verified": len(herring_reported_as_real) > 0,
        "evidence_complete_rate": round(evidence_complete / len(verified), 2) if verified else None,
        "chains_found": len(report["chains"]),
    }


if __name__ == "__main__":
    target = os.environ.get("TARGET_URL", "http://127.0.0.1:5001")
    findings_path = "evals/results/findings.json"
    score_path = "evals/results/scorecard.json"

    t0 = time.time()
    report = run_and_save(target, findings_path)
    elapsed = round(time.time() - t0, 2)

    with open(os.path.join(os.path.dirname(__file__), "ground_truth.json")) as f:
        gt = json.load(f)

    scorecard = score(report, gt)
    scorecard["run_time_seconds"] = elapsed
    with open(score_path, "w") as f:
        json.dump(scorecard, f, indent=2)

    print(json.dumps(scorecard, indent=2))

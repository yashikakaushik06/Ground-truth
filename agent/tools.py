"""
The only tool the agent gets: send an HTTP request to the target and return
what actually came back. Deliberately restricted to a single allow-listed
base_url so nothing this pipeline does can ever touch a host other than the
practice target it was pointed at.
"""
import requests


class HttpTool:
    def __init__(self, base_url, allowed_hosts=None):
        self.base_url = base_url.rstrip("/")
        # simple safety rail: refuse to fire requests anywhere but the
        # configured target, even if a request dict tries to smuggle a full URL
        self.allowed_hosts = allowed_hosts or [base_url]

    def request(self, spec: dict) -> dict:
        method = spec.get("method", "GET").upper()
        path = spec["path"]
        if path.startswith("http"):
            if not any(path.startswith(h) for h in self.allowed_hosts):
                return {"status": None, "error": "blocked: host not in allow-list"}
            url = path
        else:
            url = self.base_url + path
        try:
            resp = requests.request(
                method,
                url,
                headers=spec.get("headers", {}),
                json=spec.get("body") if spec.get("body") is not None else None,
                params=spec.get("params"),
                timeout=5,
            )
        except requests.RequestException as e:
            return {"status": None, "error": str(e)}
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        return {"status": resp.status_code, "body": body, "headers": dict(resp.headers)}

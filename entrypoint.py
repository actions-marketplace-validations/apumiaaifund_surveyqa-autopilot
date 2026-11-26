import hashlib
import os
import sys

import httpx
import pandas as pd

from core.engine import AuditResult, compile_spec, run_audit, simulate_survey


def _load_dataset(resp_p: str | None, surv_p: str | None) -> pd.DataFrame:
    if resp_p and os.path.exists(resp_p):
        return pd.read_csv(resp_p)
    if surv_p and os.path.exists(surv_p):
        return simulate_survey(surv_p, 500)
    print("Error: neither responses_path nor survey_path exists")
    sys.exit(1)


def _stamp_notary(
    status: str, n_url: str | None, n_key: str | None, bundle_hash: str
) -> str:
    if status != "PASS" or not n_url or not n_key:
        return "Skipped"
    r = httpx.post(
        n_url,
        headers={"Authorization": f"Bearer {n_key}", "User-Agent": "SurveyQA-Autopilot/1.0"},
        json={
            "sha256_hash": bundle_hash,
            "metadata": {"repository": os.getenv("GITHUB_REPOSITORY", "")},
        },
        timeout=15,
    )
    if r.status_code in (401, 403):
        sys.exit(1)
    return str(r.json().get("certificate_url", f"hash://{bundle_hash}"))


def _publish_summary(res: AuditResult, bundle_hash: str, cert: str) -> None:
    lines = [
        f"### {res.overall_status} | SHA-256: `{bundle_hash}` | Cert: {cert}",
        *[
            f"- {c.metric_name}: {c.actual} (plan {c.expected}) -> {c.status}"
            for c in res.checks
        ],
    ]
    out = "\n".join(lines)
    print(out)
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(out + "\n")


def main() -> None:
    spec_p = os.getenv("INPUT_SPEC_PATH")
    if not spec_p or not os.path.exists(spec_p):
        print("Error: spec_path is missing or file does not exist")
        sys.exit(1)

    spec = compile_spec(spec_p)
    df = _load_dataset(os.getenv("INPUT_RESPONSES_PATH"), os.getenv("INPUT_SURVEY_PATH"))
    res = run_audit(df, spec)

    bundle_hash = hashlib.sha256(res.model_dump_json().encode()).hexdigest()
    cert = _stamp_notary(
        res.overall_status,
        os.getenv("INPUT_NOTARY_API_URL"),
        os.getenv("INPUT_NOTARY_API_KEY"),
        bundle_hash,
    )
    _publish_summary(res, bundle_hash, cert)
    sys.exit(0 if res.overall_status == "PASS" else 1)


if __name__ == "__main__":
    main()

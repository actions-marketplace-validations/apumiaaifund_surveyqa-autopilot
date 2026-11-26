import hashlib
import os
import sys

import httpx
import pandas as pd
from fpdf import FPDF

from core.engine import AuditResult, compile_spec, run_audit, simulate_survey


def _read_tabular_file(path: str, is_pro: bool) -> pd.DataFrame:
    low = path.lower()
    if low.endswith(".sav"):
        if not is_pro:
            print("Error: IBM SPSS (.sav) requires a Pro License ($199) from Lava.top")
            sys.exit(1)
        return pd.read_spss(path, convert_categoricals=False)
    if low.endswith((".xlsx", ".xls")):
        if not is_pro:
            print("Error: Excel (.xlsx) requires a Pro License ($199) from Lava.top")
            sys.exit(1)
        return pd.read_excel(path)
    return pd.read_csv(path)


def _load_dataset(resp_p: str | None, surv_p: str | None, is_pro: bool) -> pd.DataFrame:
    if resp_p and os.path.exists(resp_p):
        return _read_tabular_file(resp_p, is_pro)
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
        headers={"Authorization": f"Bearer {n_key}", "User-Agent": "SurveyQA-Autopilot/2.0"},
        json={
            "sha256_hash": bundle_hash,
            "metadata": {"repository": os.getenv("GITHUB_REPOSITORY", "")},
        },
        timeout=15,
    )
    if r.status_code in (401, 403):
        sys.exit(1)
    try:
        return str(r.json().get("certificate_url", f"hash://{bundle_hash}"))
    except ValueError:
        return f"hash://{bundle_hash}"


def _generate_pdf_report(res: AuditResult, bundle_hash: str, cert: str, out_path: str) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"SurveyQA + AI Notary Compliance Certificate ({res.overall_status})", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"SHA-256 Hash: {bundle_hash}", ln=True)
    pdf.cell(0, 8, f"Verification URL: {cert}", ln=True)
    pdf.cell(0, 8, f"Total Completes Audited: {res.total_completes}", ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, "Metric Checks:", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for c in res.checks:
        pdf.cell(0, 7, f"[{c.status}] {c.category} | {c.metric_name}: {c.actual} (Plan: {c.expected})", ln=True)
    pdf.output(out_path)


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

    n_key = os.getenv("INPUT_NOTARY_API_KEY") or ""
    is_pro = n_key.startswith("sqa_pro_")
    spec = compile_spec(spec_p)
    df = _load_dataset(os.getenv("INPUT_RESPONSES_PATH"), os.getenv("INPUT_SURVEY_PATH"), is_pro)
    res = run_audit(df, spec)

    bundle_hash = hashlib.sha256(res.model_dump_json().encode()).hexdigest()
    cert = _stamp_notary(res.overall_status, os.getenv("INPUT_NOTARY_API_URL"), n_key, bundle_hash)
    if is_pro and res.overall_status == "PASS":
        _generate_pdf_report(res, bundle_hash, cert, "surveyqa-certificate.pdf")
    _publish_summary(res, bundle_hash, cert)
    sys.exit(0 if res.overall_status == "PASS" else 1)


if __name__ == "__main__":
    main()

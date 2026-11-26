import random
import re
from decimal import Decimal
from typing import Any

import defusedxml.ElementTree as ET
import pandas as pd
from docx import Document
from pydantic import BaseModel
from scipy.stats import chisquare


class MetricCheck(BaseModel):
    category: str
    metric_name: str
    expected: str
    actual: str
    delta: str
    status: str


class AuditResult(BaseModel):
    overall_status: str
    total_completes: int
    critical_errors_count: int
    checks: list[MetricCheck]


def _parse_quota_row(
    row: Any, current_var: str | None, quotas: dict[str, dict[str, Decimal]]
) -> str | None:
    cells: list[str] = [c.text.strip() for c in row.cells]
    if len(cells) < 3:
        return current_var
    var_cell, category, pct_cell = cells[:3]
    var_name: str | None = var_cell or current_var
    pct_str: str = re.sub(r"[^\d.]", "", pct_cell)
    if var_name and category and pct_str:
        quotas.setdefault(var_name, {})[category] = Decimal(pct_str)
    return var_name


def _parse_quota_table(table: Any, quotas: dict[str, dict[str, Decimal]]) -> None:
    first_row = next(iter(table.rows), None)
    if not first_row:
        return
    headers = " ".join(c.text.lower() for c in first_row.cells)
    if "quota" not in headers and "%" not in headers:
        return
    current_var: str | None = None
    for row in list(table.rows)[1:]:
        current_var = _parse_quota_row(row, current_var, quotas)


def compile_spec(docx_path: str) -> dict[str, Any]:
    doc = Document(docx_path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    loi_match = re.search(r"LOI\s*[:=]\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    rand_vars = list(
        set(re.findall(r"\[RANDOMIZE:\s*([a-zA-Z0-9_]+)\]", text, re.IGNORECASE))
    )
    quotas: dict[str, dict[str, Decimal]] = {}
    for table in doc.tables:
        _parse_quota_table(table, quotas)
    return {
        "loi": Decimal(loi_match.group(1)) if loi_match else Decimal(10),
        "quotas": quotas,
        "rand": rand_vars,
    }


def simulate_survey(xml_path: str, n: int = 500) -> pd.DataFrame:
    random.seed(42)
    root = ET.parse(xml_path).getroot()
    questions = [
        {
            "label": elem.attrib["label"],
            "shuffle": elem.attrib.get("shuffle", "none") != "none",
            "opts": [
                r.attrib.get("value", str(i + 1))
                for i, r in enumerate(elem.findall("./row"))
            ]
            or ["1", "2", "3", "4"],
        }
        for elem in root.findall(".//*[@label]")
        if elem.tag.lower() in {"radio", "checkbox", "select"}
    ]

    rows = []
    for i in range(1, n + 1):
        row: dict[str, Any] = {
            "respondent_id": f"sim_{i}",
            "status": "complete",
            "duration_sec": max(60, int(random.gauss(600, 120))),
        }
        for q in questions:
            opts = list(q["opts"])
            if q["shuffle"]:
                random.shuffle(opts)
            row[q["label"]] = random.choice(opts)
        rows.append(row)
    return pd.DataFrame(rows)


def _check_single_quota_var(
    comp: pd.DataFrame, var: str, targets: dict[str, Decimal]
) -> list[MetricCheck]:
    col = next((c for c in comp.columns if c.lower() == var.lower()), None)
    if not col:
        return [
            MetricCheck(
                category="Quotas",
                metric_name=var,
                expected="Exists",
                actual="Missing",
                delta="N/A",
                status="FAIL",
            )
        ]
    counts = comp[col].astype(str).value_counts()
    tolerance = Decimal("2.5")
    checks: list[MetricCheck] = []
    for cat, tgt in targets.items():
        cat_count = int(counts.get(str(cat), 0))
        basis_points = (cat_count * 10000) // len(comp)
        act = Decimal(basis_points).scaleb(-2)
        delta = (act - tgt).quantize(Decimal("0.01"))
        checks.append(
            MetricCheck(
                category="Quotas",
                metric_name=f"{var}={cat}",
                expected=f"{tgt}%",
                actual=f"{act}%",
                delta=f"{delta:+}%",
                status="PASS" if abs(delta) <= tolerance else "FAIL",
            )
        )
    return checks


def _evaluate_quotas(
    comp: pd.DataFrame, quotas: dict[str, dict[str, Decimal]]
) -> list[MetricCheck]:
    checks: list[MetricCheck] = []
    for var, targets in quotas.items():
        checks.extend(_check_single_quota_var(comp, var, targets))
    return checks


def _evaluate_randomization(
    comp: pd.DataFrame, rand_vars: list[str]
) -> list[MetricCheck]:
    checks: list[MetricCheck] = []
    alpha = Decimal("0.05")
    for var in rand_vars:
        col = next((c for c in comp.columns if c.lower() == var.lower()), None)
        if not col:
            continue
        counts = comp[col].dropna().value_counts().values
        if len(counts) > 1:
            _, p_val = chisquare(counts)
            p_dec = Decimal(str(p_val)).quantize(Decimal("0.001"))
            checks.append(
                MetricCheck(
                    category="Logic",
                    metric_name=f"Random {var}",
                    expected="p>0.05",
                    actual=f"p={p_dec}",
                    delta="OK",
                    status="PASS" if p_dec > alpha else "FAIL",
                )
            )
    return checks


def run_audit(df: pd.DataFrame, spec: dict[str, Any]) -> AuditResult:
    scol = next((c for c in df.columns if c.lower() in {"status", "vstatus"}), None)
    comp = (
        df[df[scol].astype(str).str.lower().isin({"complete", "1", "finished"})]
        if scol
        else df
    )
    total_n = len(comp)
    if total_n == 0:
        return AuditResult(
            overall_status="BLOCK",
            total_completes=0,
            critical_errors_count=1,
            checks=[
                MetricCheck(
                    category="Base",
                    metric_name="Completes",
                    expected=">0",
                    actual="0",
                    delta="0",
                    status="FAIL",
                )
            ],
        )

    checks = _evaluate_quotas(comp, spec["quotas"]) + _evaluate_randomization(
        comp, spec["rand"]
    )
    fails = sum(1 for c in checks if c.status == "FAIL")
    return AuditResult(
        overall_status="BLOCK" if fails > 0 else "PASS",
        total_completes=total_n,
        critical_errors_count=fails,
        checks=checks,
    )

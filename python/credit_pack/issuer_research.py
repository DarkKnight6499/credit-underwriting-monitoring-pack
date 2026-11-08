"""Auditable public fact selections and illustrative buy/hold/sell scorecards."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import extension_config as cfg
from .extension_config import X
from .ratios import divide

# CONFIG: manually verified fact snapshot and synthetic bond spread scenarios.
FACTS_FILE = cfg.INPUT / "public_issuer_facts.json"
MANIFEST_FILE = cfg.INPUT / "manifest.json"
ISSUER_CASES = (
    {X.ISSUER: "Apple", X.KIND: "corporate", X.SPREAD: .0006,
     "risk": "Product concentration, competition, and shareholder distributions.",
     "catalyst": "Review new annual cash flow and capital allocation before adding exposure.",
     "monitor": "FCF/debt below 0.8 or leverage above 1.5x."},
    {X.ISSUER: "JPMorgan Chase", X.KIND: "gsib", X.SPREAD: .0018,
     "risk": "Funding outflows, market risk, credit losses, and holding company structural subordination.",
     "catalyst": "Synthetic spread compensates for the two-factor score under the chosen policy.",
     "monitor": "LCR below 1.05 or CET1 below 12%; these are scenario triggers, not regulatory minima."},
    {X.ISSUER: "Dutchess County", X.KIND: "go", X.SPREAD: .0015,
     "risk": "General Fund deficit and declining unassigned balance; pensions and debt service are not reviewed.",
     "catalyst": "A restored operating surplus would support reconsideration.",
     "monitor": "Further deficit, sales-tax weakness, or fund balance/revenue below 10%."},
    {X.ISSUER: "NYC Water and Sewer System", X.KIND: "revenue", X.SPREAD: .0004,
     "risk": "High debt burden, capital needs, affordability, and restricted cash.",
     "catalyst": "Require verified bond-specific coverage and sufficient spread before adding exposure.",
     "monitor": "Operating margin below 30% or debt/revenue above 8x."},
)


def load_facts(path=FACTS_FILE, manifest_path=MANIFEST_FILE) -> pd.DataFrame:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = path.read_bytes()
    records = [item for item in manifest if Path(item["path"]).name == path.name]
    if len(records) != 1:
        raise ValueError("The public snapshot needs exactly one matching manifest record.")
    record = records[0]
    if hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise ValueError("Public fact snapshot hash mismatch.")
    result = pd.DataFrame(json.loads(raw))
    if result.duplicated([X.ISSUER, X.METRIC]).any() or result[X.VALUE].isna().any():
        raise ValueError("Public facts need unique nonmissing issuer/metric keys.")
    if (pd.to_datetime(result[X.END]) > pd.Timestamp(cfg.AS_OF)).any():
        raise ValueError("Future public facts are not permitted.")
    return result


def metrics(kind: str, values: dict) -> dict:
    if kind == "corporate":
        debt = values[X.DEBT_CURRENT] + values[X.DEBT_LONG] + values[X.DEBT_SHORT]
        ebitda = values[X.OP_INCOME] + values[X.DA]
        return {X.DEBT: debt, X.EBITDA: ebitda, X.LEVERAGE: divide(debt, ebitda),
                X.FCF_DEBT: divide(values[X.CFO] - values[X.CAPEX], debt)}
    if kind == "gsib":
        return {X.CET1: values[X.CET1], X.LCR: values[X.LCR]}
    if kind == "go":
        return {X.FUND_RATIO: divide(values[X.FUND_BALANCE], values[X.REVENUE]),
                X.OPERATING_BALANCE: divide(values[X.REVENUE] - values[X.OPEX], values[X.REVENUE])}
    if kind == "revenue":
        return {X.CASH_MARGIN: divide(values[X.REVENUE] - values[X.OPEX], values[X.REVENUE]),
                X.DEBT_REVENUE: divide(values[X.DEBT], values[X.REVENUE])}
    raise ValueError("Unsupported issuer type.")


def scorecard(kind: str, inputs: dict, spread: float) -> tuple[dict, pd.DataFrame]:
    if not math.isfinite(spread):
        raise ValueError("Finite synthetic spread required.")
    rows = []
    for metric, (higher_better, boundaries) in cfg.SCORE_FACTORS[kind].items():
        value = inputs.get(metric, np.nan)
        missing = not math.isfinite(value)
        score = 4 if missing else (4 - sum(value >= b for b in boundaries) if higher_better
                                   else 1 + sum(value > b for b in boundaries))
        rows.append({X.FACTOR: metric, X.VALUE: value, X.FACTOR_SCORE: score,
                     X.WEIGHT: 1 / len(cfg.SCORE_FACTORS[kind]), X.FLAGS: "missing_input" if missing else ""})
    factors = pd.DataFrame(rows)
    average = float((factors[X.FACTOR_SCORE] * factors[X.WEIGHT]).sum())
    incomplete = factors[X.FLAGS].ne("").any()
    call = ("review required" if incomplete else "sell" if average > cfg.SCORE_HOLD_MAX else
            "buy" if average <= cfg.SCORE_BUY_MAX and spread >= cfg.SCORE_MIN_SPREAD else "hold")
    return {X.SCORE_AVG: average, X.SPREAD: spread, X.RECOMMENDATION: call}, factors


def run_research() -> dict:
    facts = load_facts()
    summaries, factors = [], []
    for case in ISSUER_CASES:
        selected = facts.loc[facts[X.ISSUER].eq(case[X.ISSUER])]
        values = selected.set_index(X.METRIC)[X.VALUE].to_dict()
        financial = metrics(case[X.KIND], values)
        result, detail = scorecard(case[X.KIND], financial, case[X.SPREAD])
        summaries.append({X.ISSUER: case[X.ISSUER], X.KIND: case[X.KIND], **financial, **result,
                          X.END: selected[X.END].max(), X.SOURCE: "Public facts; synthetic spread and score policy"})
        detail[X.ISSUER] = case[X.ISSUER]
        factors.append(detail)
    return {"issuer_facts": facts, "issuer_scorecards": pd.DataFrame(summaries),
            "issuer_factors": pd.concat(factors, ignore_index=True)}

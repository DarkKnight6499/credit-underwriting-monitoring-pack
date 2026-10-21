"""Select annual entity-wide USD facts and retain value-level lineage."""

from datetime import date

import numpy as np
import pandas as pd

from . import config as cfg
from .config import C


def acceptable(fact: dict, instant: bool) -> bool:
    if fact.get("form") != cfg.FORM or fact.get("fp") != cfg.FISCAL_PERIOD:
        return False
    try:
        end = date.fromisoformat(fact["end"])
        filed = date.fromisoformat(fact["filed"])
        if end > date.fromisoformat(cfg.AS_OF) or filed > date.fromisoformat(cfg.AS_OF):
            return False
        if filed < end:
            return False
        if instant:
            return "start" not in fact
        duration = (end - date.fromisoformat(fact["start"])).days + 1
        return cfg.ANNUAL_MIN_DAYS <= duration <= cfg.ANNUAL_MAX_DAYS
    except (KeyError, ValueError, TypeError):
        return False


def tag_facts(companyfacts: dict, tag: str) -> list[dict]:
    return companyfacts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get(cfg.UNIT, [])


def fiscal_periods(companyfacts: dict) -> list[tuple[int, str]]:
    # The earliest original annual context anchors the fiscal label, avoiding later comparative FY labels.
    by_end = {}
    for tag in cfg.TAGS[C.REVENUE]:
        for fact in tag_facts(companyfacts, tag):
            if acceptable(fact, False) and isinstance(fact.get("fy"), int):
                previous = by_end.get(fact["end"])
                if previous is None or fact["filed"] < previous["filed"]:
                    by_end[fact["end"]] = fact
    periods = [(fact["fy"], end) for end, fact in sorted(by_end.items())][-cfg.YEARS:]
    if len(periods) != cfg.YEARS or len({year for year, _ in periods}) != cfg.YEARS:
        raise ValueError(f"Expected {cfg.YEARS} distinct annual revenue periods; found {periods}.")
    return periods


def select_fact(companyfacts: dict, metric: str, year: int, end: str) -> tuple[float, str, dict]:
    for tag in cfg.TAGS[metric]:
        candidates = [fact for fact in tag_facts(companyfacts, tag)
                      if acceptable(fact, metric in cfg.INSTANT_METRICS)
                      and fact.get("fy") == year and fact.get("end") == end]
        if candidates:
            fact = max(candidates, key=lambda row: (row["filed"], row.get("accn", "")))
            return float(fact["val"]), tag, fact
    return np.nan, "MISSING", {}


def spread(companyfacts: dict, ticker: str, source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, lineage = [], []
    for year, end in fiscal_periods(companyfacts):
        row = {C.TICKER: ticker, C.YEAR: year, C.END: end, C.SOURCE: source}
        flags = []
        for metric in cfg.TAGS:
            value, tag, fact = select_fact(companyfacts, metric, year, end)
            if not np.isfinite(value):
                flags.append(f"missing:{metric}")
                if metric in cfg.DEBT_COMPONENTS:
                    value = 0.0
                    flags.append(f"zero_assumed:{metric}")
            row[metric] = value
            lineage.append({C.TICKER: ticker, C.YEAR: year, C.END: end,
                            C.METRIC: metric, C.VALUE: value, C.TAG: tag,
                            C.START: fact.get("start", ""), C.FILED: fact.get("filed", ""),
                            C.ACCESSION: fact.get("accn", ""), C.SOURCE: source})
        row[C.DEBT] = sum(row[metric] for metric in cfg.DEBT_COMPONENTS)
        row[C.FLAGS] = ";".join(flags)
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(lineage)


def synthetic_companyfacts(ticker: str, seed: int) -> dict:
    """Create illustrative test data; ticker labels do not imply actual issuer figures."""
    rng = np.random.default_rng(seed)
    assumptions = cfg.BORROWERS[ticker]
    payload = {"entityName": f"{ticker} SYNTHETIC", "facts": {"us-gaap": {}}}
    for offset, year in enumerate(cfg.DEMO_YEARS):
        revenue = assumptions["base_revenue"] * (1 + assumptions["growth"]) ** offset
        margin = assumptions["base_margin"] + rng.normal(0, assumptions["volatility"])
        ebitda = revenue * margin
        debt = ebitda * assumptions["debt_multiple"] * (1 + cfg.DEMO_DEBT_TREND * offset)
        values = {metric: revenue * ratio for metric, ratio in cfg.DEMO_BALANCE_RATIOS.items()}
        values.update({C.REVENUE: revenue, C.OP_INCOME: ebitda - values[C.DA],
                       C.INTEREST: debt * cfg.DEMO_INTEREST_RATE,
                       C.TAX: max(0, ebitda - values[C.DA]) * cfg.DEMO_CASH_TAX_RATE,
                       C.DEBT_LONG: debt * (1 - cfg.DEMO_CURRENT_DEBT_SHARE),
                       C.DEBT_CURRENT: debt * cfg.DEMO_CURRENT_DEBT_SHARE,
                       C.CFO: ebitda * cfg.DEMO_CFO_CONVERSION})
        for metric, value in values.items():
            tag = cfg.TAGS[metric][-1] if metric in (C.REVENUE, C.COGS) else cfg.TAGS[metric][0]
            fact = {"fy": year, "fp": cfg.FISCAL_PERIOD, "form": cfg.FORM,
                    "end": f"{year}-12-31", "filed": f"{year + 1}-02-20",
                    "val": value, "accn": f"SYNTHETIC-{ticker}-{year}"}
            if metric not in cfg.INSTANT_METRICS:
                fact["start"] = f"{year}-01-01"
            taxonomy = payload["facts"]["us-gaap"]
            taxonomy.setdefault(tag, {"units": {cfg.UNIT: []}})["units"][cfg.UNIT].append(fact)
    return payload

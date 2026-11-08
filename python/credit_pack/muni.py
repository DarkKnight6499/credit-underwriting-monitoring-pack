"""GO and revenue scenarios with explicit pledge and tax assumptions."""

import math

import pandas as pd

from . import extension_config as cfg
from .extension_config import X
from .ratios import divide

# CONFIG: synthetic muni examples and matched yield comparison assumptions.
GO_INPUT = {X.ISSUER: "Synthetic County", X.REVENUE: 120e6, X.OPEX: 118e6,
            X.FUND_BALANCE: 18e6, X.DEBT: 90e6, X.ASSESSED_VALUE: 4e9,
            X.COLLECTION_RATE: .98}
REVENUE_INPUT = {X.ISSUER: "Synthetic Water Utility", X.REVENUE: 30e6, X.OPEX: 17e6,
                 X.MAINT_CONTRIB: 1e6, X.SERVICE: 8e6, X.CASH: 9e6,
                 X.DSCR_MIN: 1.20}
MUNI_YIELDS = (.032, .038)
TAXABLE_COMPARATOR = .05


def go_analysis(inputs: dict) -> dict:
    row = dict(inputs)
    required = (X.REVENUE, X.OPEX, X.FUND_BALANCE, X.DEBT, X.ASSESSED_VALUE, X.COLLECTION_RATE)
    if not all(math.isfinite(row[k]) for k in required) or row[X.REVENUE] <= 0 or row[X.ASSESSED_VALUE] <= 0:
        raise ValueError("Finite GO inputs and positive revenue and assessed value are required.")
    if min(row[X.OPEX], row[X.DEBT]) < 0 or not 0 <= row[X.COLLECTION_RATE] <= 1:
        raise ValueError("Invalid GO expense, debt, or tax collection rate.")
    row.update({X.KIND: "go", X.FUND_RATIO: row[X.FUND_BALANCE] / row[X.REVENUE],
                X.OPERATING_BALANCE: (row[X.REVENUE] - row[X.OPEX]) / row[X.REVENUE],
                X.DEBT_REVENUE: row[X.DEBT] / row[X.REVENUE],
                X.DEBT_VALUE: row[X.DEBT] / row[X.ASSESSED_VALUE]})
    return row


def revenue_analysis(inputs: dict, revenue_change=0.0) -> dict:
    row = dict(inputs)
    required = (X.REVENUE, X.OPEX, X.MAINT_CONTRIB, X.SERVICE, X.CASH, X.DSCR_MIN)
    if (not all(math.isfinite(row[k]) for k in required) or min(row[k] for k in required) < 0
            or row[X.SERVICE] <= 0 or row[X.REVENUE] <= 0 or row[X.DSCR_MIN] <= 0
            or not math.isfinite(revenue_change) or revenue_change <= -1):
        raise ValueError("Invalid revenue credit inputs.")
    revenue = row[X.REVENUE] * (1 + revenue_change)
    cfads = revenue - row[X.OPEX] - row[X.MAINT_CONTRIB]
    row.update({X.KIND: "revenue", X.REVENUE: revenue, X.CFADS: cfads,
                X.DSCR: cfads / row[X.SERVICE], X.REVENUE_CHANGE: revenue_change,
                X.DAYS_CASH: divide(row[X.CASH] * cfg.DAYS, row[X.OPEX]),
                X.BREACH: bool(cfads < row[X.DSCR_MIN] * row[X.SERVICE]),
                X.BREAK_EVEN: 1 - (row[X.OPEX] + row[X.MAINT_CONTRIB]
                                   + row[X.DSCR_MIN] * row[X.SERVICE]) / inputs[X.REVENUE]})
    return row


def tax_equivalent_yield(muni_yield: float, tax_rate: float, tax_exempt=True) -> float:
    if not math.isfinite(muni_yield) or not math.isfinite(tax_rate) or not 0 <= tax_rate < 1:
        raise ValueError("Yield must be finite and tax rate in [0, 1).")
    return muni_yield / (1 - tax_rate) if tax_exempt else muni_yield


def relative_value(muni_yield: float, taxable_yield: float, tax_rate: float,
                   tax_exempt=True) -> dict:
    if not math.isfinite(taxable_yield) or taxable_yield <= 0:
        raise ValueError("Positive finite comparator yield required.")
    tey = tax_equivalent_yield(muni_yield, tax_rate, tax_exempt)
    return {X.YIELD: muni_yield, X.TAXABLE_YIELD: taxable_yield, X.TAX_RATE: tax_rate,
            X.TAX_EXEMPT: tax_exempt, X.TEY: tey, X.TEY_SPREAD: tey - taxable_yield,
            X.MUNI_RATIO: muni_yield / taxable_yield}


def run_muni() -> dict:
    return {"muni_go": pd.DataFrame([go_analysis(GO_INPUT)]),
            "muni_revenue": pd.DataFrame([revenue_analysis(REVENUE_INPUT, shock)
                                           for shock in cfg.REVENUE_STRESSES]),
            "muni_relative_value": pd.DataFrame([relative_value(yield_value, TAXABLE_COMPARATOR, rate)
                                                 for yield_value in MUNI_YIELDS for rate in cfg.TAX_RATES])}

"""Illustrative rent rolls and three-constraint CRE sizing."""

import math

import pandas as pd

from . import config as cfg
from .config import C


def debt_constant(annual_rate: float, amortization_years: int) -> float:
    if annual_rate < 0 or amortization_years <= 0:
        raise ValueError("Rate must be nonnegative and amortization years positive.")
    periods = cfg.MONTHS_IN_YEAR * amortization_years
    if annual_rate == 0:
        return cfg.MONTHS_IN_YEAR / periods
    monthly_rate = annual_rate / cfg.MONTHS_IN_YEAR
    return cfg.MONTHS_IN_YEAR * monthly_rate / (1 - (1 + monthly_rate) ** (-periods))


def supervisory_flag(category: str, ltv: float) -> tuple[float | None, bool]:
    limit = cfg.SUPERVISORY_LTV[category]
    return limit, limit is not None and ltv > limit


def size_loan(noi: float, cap_rate: float, ltv_limit=cfg.CRE_LTV_LIMIT,
              dscr_min=cfg.CRE_DSCR_MIN, annual_rate=cfg.CRE_RATE,
              amortization_years=cfg.CRE_AMORT_YEARS, debt_yield_min=cfg.CRE_YIELD_MIN) -> dict:
    values = (noi, cap_rate, ltv_limit, dscr_min, debt_yield_min)
    if not all(math.isfinite(value) and value > 0 for value in values):
        raise ValueError("NOI, cap rate, and sizing limits must be finite and positive.")
    if ltv_limit > 1:
        raise ValueError("LTV limit must not exceed one.")
    constant = debt_constant(annual_rate, amortization_years)
    value = noi / cap_rate
    constraints = {C.LTV_LOAN: ltv_limit * value, C.DSCR_LOAN: noi / (dscr_min * constant),
                   C.YIELD_LOAN: noi / debt_yield_min}
    binding = min(constraints, key=constraints.get)
    loan = constraints[binding]
    stressed_constant = debt_constant(annual_rate + cfg.CRE_RATE_STRESS, amortization_years)
    return {C.NOI: noi, C.CAP_RATE: cap_rate, C.LTV_LIMIT: ltv_limit, C.DSCR_MIN: dscr_min,
            C.RATE: annual_rate, C.AMORT_YEARS: amortization_years, C.YIELD_MIN: debt_yield_min,
            C.VALUE: value, C.DEBT_CONSTANT: constant, **constraints, C.LOAN: loan,
            C.BINDING: binding, C.LTV: loan / value, C.DSCR: noi / (loan * constant),
            C.DEBT_YIELD: noi / loan,
            C.STRESS_DSCR: noi * (1 + cfg.CRE_NOI_STRESS) / (loan * stressed_constant)}


def property_cashflow(property_inputs: dict) -> dict:
    row = dict(property_inputs)
    row[C.PGI] = row[C.QUANTITY] * row[C.RENT]
    row[C.EGI] = row[C.PGI] * (1 - row[C.VACANCY]) + row[C.OTHER_INCOME]
    row[C.NOI] = row[C.EGI] - row[C.OPEX] - row[C.RESERVES]
    return row


def run_properties() -> tuple[pd.DataFrame, pd.DataFrame]:
    rolls, sizes = [], []
    for inputs in cfg.PROPERTIES:
        row = property_cashflow(inputs)
        result = size_loan(row[C.NOI], row[C.CAP_RATE])
        limit, flag = supervisory_flag(row[C.CATEGORY], result[C.LTV])
        result.update({C.PROPERTY: row[C.PROPERTY], C.PROPERTY_TYPE: row[C.PROPERTY_TYPE],
                       C.CATEGORY: row[C.CATEGORY], C.SUPERVISORY_LIMIT: limit, C.SUPERVISORY_FLAG: flag})
        rolls.append(row)
        sizes.append(result)
    return pd.DataFrame(rolls), pd.DataFrame(sizes)

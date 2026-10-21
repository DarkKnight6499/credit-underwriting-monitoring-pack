"""Illustrative replacement financing, amortization, covenants, and downside."""

import numpy as np
import pandas as pd

from . import config as cfg
from .config import C
from .ratios import divide


def covenant_headroom(debt: float, ebitda: float, fccr: float,
                      max_leverage=cfg.MAX_LEVERAGE, min_fccr=cfg.MIN_FCCR) -> dict:
    leverage = divide(debt, ebitda)
    cushion = 1 - divide(debt, max_leverage * ebitda)
    leverage_breach = not np.isfinite(leverage) or leverage > max_leverage
    fccr_breach = not np.isfinite(fccr) or fccr < min_fccr
    return {C.DEBT: debt, C.EBITDA: ebitda, C.LEVERAGE: leverage, C.FCCR: fccr,
            C.MAX_LEVERAGE: max_leverage, C.MIN_FCCR: min_fccr,
            C.LEVERAGE_HEADROOM: divide(max_leverage - leverage, max_leverage),
            C.FCCR_HEADROOM: divide(fccr - min_fccr, min_fccr), C.CUSHION: cushion,
            C.LEVERAGE_BREACH: leverage_breach, C.FCCR_BREACH: fccr_breach,
            C.BREACH: leverage_breach or fccr_breach}


def propose(financial: dict) -> tuple[dict, pd.DataFrame]:
    ebitda = financial[C.EBITDA]
    if not np.isfinite(ebitda) or ebitda <= 0:
        raise ValueError("Positive, available EBITDA required to size a facility.")
    revolver = ebitda * cfg.REVOLVER_MULTIPLE
    term = ebitda * cfg.TERM_MULTIPLE
    drawn = term + revolver * cfg.REVOLVER_UTILIZATION
    principal = term / cfg.TERM_YEARS
    interest = drawn * cfg.FACILITY_RATE
    # Historical debt is assumed refinanced; uncovered debt is a closing equity requirement.
    equity_call = max(0, financial[C.DEBT] - drawn)
    fccr = divide(ebitda - financial[C.CAPEX] - financial[C.TAX], interest + principal)
    result = covenant_headroom(drawn, ebitda, fccr)
    result.update({C.REVOLVER: revolver, C.TERM: term, C.PROPOSED_DEBT: drawn,
                   C.PRINCIPAL: principal, C.INTEREST: interest, C.EQUITY_CALL: equity_call,
                   C.RATE: cfg.FACILITY_RATE, C.AMORT_YEARS: cfg.TERM_YEARS,
                   C.REVOLVER_UTILIZATION: cfg.REVOLVER_UTILIZATION,
                   C.REVENUE_STRESS: cfg.REVENUE_STRESS, C.MARGIN_STRESS: cfg.MARGIN_STRESS,
                   C.LGD: facility_lgd_default()})
    down_revenue = financial[C.REVENUE] * (1 + cfg.REVENUE_STRESS)
    down_ebitda = down_revenue * (financial[C.MARGIN] + cfg.MARGIN_STRESS)
    down_fccr = divide(down_ebitda - financial[C.CAPEX] - financial[C.TAX], interest + principal)
    down = covenant_headroom(drawn, down_ebitda, down_fccr)
    required_ebitda = max(drawn / cfg.MAX_LEVERAGE,
                          cfg.MIN_FCCR * (interest + principal) + financial[C.CAPEX] + financial[C.TAX])
    result.update({C.DOWN_REVENUE: down_revenue, C.DOWN_EBITDA: down_ebitda,
                   C.DOWN_LEVERAGE: down[C.LEVERAGE], C.DOWN_FCCR: down_fccr,
                   C.DOWN_BREACH: down[C.BREACH], C.BREAK_EVEN: 1 - required_ebitda / ebitda})
    schedule = []
    balance = term
    for year in range(1, cfg.TERM_YEARS + 1):
        schedule.append({C.YEAR: year, C.OPENING: balance, C.PRINCIPAL: principal,
                         C.INTEREST: balance * cfg.FACILITY_RATE, C.OUTSTANDING: max(0, balance - principal)})
        balance -= principal
    return result, pd.DataFrame(schedule)


def facility_lgd_default() -> float:
    return cfg.LGD_TABLE[("senior", "all_assets")]


def recommend(rating: dict, facility: dict, incomplete: bool = False) -> str:
    if incomplete or rating[C.GRADE] > cfg.CONDITIONAL_MAX_GRADE or facility[C.BREACH]:
        return "decline"
    if (rating[C.GRADE] > cfg.APPROVE_MAX_GRADE or facility[C.DOWN_BREACH]
            or facility[C.EQUITY_CALL] > cfg.TOLERANCE):
        return "approve with conditions"
    return "approve"

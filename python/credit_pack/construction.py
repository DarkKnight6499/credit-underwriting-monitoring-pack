"""Equity-first draw controls, retainage, reserves, and loan-in-balance."""

import pandas as pd

from . import config as cfg
from .config import C


def loan_in_balance(cost_to_complete: float, undisbursed_loan: float, remaining_equity: float) -> dict:
    if min(cost_to_complete, undisbursed_loan, remaining_equity) < 0:
        raise ValueError("Balance-test inputs must be nonnegative.")
    shortfall = max(0, cost_to_complete - undisbursed_loan - remaining_equity)
    return {C.COST_COMPLETE: cost_to_complete, C.UNDISBURSED: undisbursed_loan,
            C.REMAINING_EQUITY: remaining_equity, C.SHORTFALL: shortfall,
            C.EQUITY_CALL: shortfall > cfg.TOLERANCE}


def fund_draw(approved: float, retainage=cfg.RETAINAGE) -> float:
    if approved < 0 or not 0 <= retainage <= 1:
        raise ValueError("Invalid approved draw or retainage rate.")
    return approved * (1 - retainage)


def review_line(budget: float, previously_approved: float, requested: float,
                percent_complete: float) -> tuple[float, list[str]]:
    if budget < 0 or previously_approved < 0 or requested < 0 or not 0 <= percent_complete <= 1:
        raise ValueError("Invalid construction draw inputs.")
    flags = []
    if previously_approved + requested > budget * percent_complete + cfg.TOLERANCE:
        flags.append("requested_exceeds_inspected_completion")
    if previously_approved + requested > budget + cfg.TOLERANCE:
        flags.append("line_overrun")
    approved = max(0, min(requested, budget * percent_complete - previously_approved,
                          budget - previously_approved))
    return approved, flags


def run_construction() -> tuple[pd.DataFrame, pd.DataFrame]:
    budget = cfg.CONSTRUCTION_BUDGET
    approved_by_line = dict.fromkeys(budget, 0.0)
    funded_by_line = dict.fromkeys(budget, 0.0)
    cumulative_equity = cumulative_loan = 0.0
    records, reviews = [], []
    for month in range(1, cfg.CONSTRUCTION_MONTHS + 1):
        progress = month / cfg.CONSTRUCTION_MONTHS
        month_flags = []
        for line, amount in budget.items():
            target = amount * progress
            percent = max(0, progress - cfg.CONSTRUCTION_INSPECTOR_LAG)
            if line == cfg.CONSTRUCTION_LAND_LINE:
                target, percent = amount, 1.0
            requested = max(0, target - approved_by_line[line])
            if line == cfg.CONSTRUCTION_HARD_LINE and month == cfg.CONSTRUCTION_MONTHS:
                requested += amount * cfg.CONSTRUCTION_OVERRUN
            approved, flags = review_line(amount, approved_by_line[line], requested, percent)
            retainage = cfg.RETAINAGE if line == cfg.CONSTRUCTION_HARD_LINE else 0.0
            funded = fund_draw(approved, retainage)
            equity_funded = min(funded, max(0, cfg.CONSTRUCTION_EQUITY - cumulative_equity))
            loan_funded = min(funded - equity_funded,
                              max(0, cfg.CONSTRUCTION_COMMITMENT - cumulative_loan))
            if funded - equity_funded - loan_funded > cfg.TOLERANCE:
                flags.append("insufficient_funding")
            actual_funded = equity_funded + loan_funded
            cumulative_equity += equity_funded
            cumulative_loan += loan_funded
            approved_by_line[line] += approved
            funded_by_line[line] += actual_funded
            month_flags.extend(flags)
            records.append({C.MONTH: month, C.LINE: line, C.BUDGET: amount, C.COMPLETE: percent,
                            C.REQUEST: requested, C.APPROVED: approved, C.RETAINAGE: retainage,
                            C.RETAINED: approved * retainage, C.FUNDED: actual_funded,
                            C.EQUITY_FUNDED: equity_funded, C.LOAN_FUNDED: loan_funded,
                            C.CUM_APPROVED: approved_by_line[line], C.CUM_FUNDED: funded_by_line[line],
                            C.CUM_EQUITY: cumulative_equity, C.CUM_LOAN: cumulative_loan,
                            C.FLAGS: ";".join(flags)})
        contingency_left = budget[cfg.CONSTRUCTION_CONTINGENCY_LINE] - cfg.CONSTRUCTION_CONTINGENCY_USE * progress
        interest_left = budget[cfg.CONSTRUCTION_INTEREST_LINE] - funded_by_line[cfg.CONSTRUCTION_INTEREST_LINE]
        interest_required = cfg.CONSTRUCTION_RESERVE_NEED * (1 - progress)
        # Unpaid retainage is still a project obligation and stays in cost to complete.
        forecast_total = sum(budget.values()) + budget[cfg.CONSTRUCTION_HARD_LINE] * cfg.CONSTRUCTION_OVERRUN * progress
        cost_complete = max(0, forecast_total - cumulative_equity - cumulative_loan)
        balance = loan_in_balance(cost_complete, cfg.CONSTRUCTION_COMMITMENT - cumulative_loan,
                                   cfg.CONSTRUCTION_EQUITY - cumulative_equity)
        if contingency_left <= cfg.TOLERANCE:
            month_flags.append("contingency_depleted")
        if interest_left + cfg.TOLERANCE < interest_required:
            month_flags.append("interest_reserve_shortfall")
        if balance[C.EQUITY_CALL]:
            month_flags.append("loan_out_of_balance")
        reviews.append({C.MONTH: month, **balance, C.CUM_EQUITY: cumulative_equity,
                        C.CUM_LOAN: cumulative_loan, C.CONTINGENCY_LEFT: contingency_left,
                        C.INTEREST_LEFT: interest_left, C.INTEREST_REQUIRED: interest_required,
                        C.FLAGS: ";".join(sorted(set(month_flags)))})
    return pd.DataFrame(records), pd.DataFrame(reviews)

"""Seeded loan histories with type-specific tests and quarterly monitoring."""

import numpy as np
import pandas as pd

from . import config as cfg
from .config import C
from .abl import certificate, synthetic_aging
from .construction import loan_in_balance
from .cre import debt_constant, supervisory_flag
from .facility import covenant_headroom


def watchlist_triggers(row: dict) -> list[str]:
    triggers = []
    if row[C.CHANGE] >= cfg.WATCH_DOWNGRADE:
        triggers.append("downgrade_2_or_more")
    if row[C.BREACH]:
        triggers.append("covenant_breach")
    if row[C.LOAN_TYPE] == "cre" and row[C.DSCR] < cfg.WATCH_DSCR:
        triggers.append("dscr_below_1")
    if row[C.LOAN_TYPE] == "abl" and row[C.AVAILABILITY] < cfg.SPRINGING_THRESHOLD * row[C.COMMITMENT]:
        triggers.append("abl_low_availability")
    if row[C.PROPERTY_TYPE] == "construction" and row[C.SHORTFALL] > cfg.TOLERANCE:
        triggers.append("construction_out_of_balance")
    if row[C.SUPERVISORY_FLAG]:
        triggers.append("supervisory_ltv_exception")
    return triggers


def synthetic_portfolio() -> pd.DataFrame:
    rng = np.random.default_rng(cfg.SEED)
    quarters = pd.period_range(cfg.PORTFOLIO_START, periods=cfg.PORTFOLIO_QUARTERS, freq="Q")
    rows = []
    for number in range(cfg.PORTFOLIO_LOANS):
        loan_type = cfg.LOAN_TYPES[number % len(cfg.LOAN_TYPES)]
        property_type = (cfg.PORTFOLIO_PROPERTY_TYPES[(number // len(cfg.LOAN_TYPES)) % len(cfg.PORTFOLIO_PROPERTY_TYPES)]
                         if loan_type == "cre" else "not_applicable")
        industry = cfg.PORTFOLIO_INDUSTRIES[number % len(cfg.PORTFOLIO_INDUSTRIES)]
        if loan_type == "cre":
            industry = cfg.PORTFOLIO_CRE_INDUSTRY
        elif loan_type == "abl":
            industry = cfg.PORTFOLIO_ABL_INDUSTRY
        base_balance = rng.uniform(*cfg.PORTFOLIO_BALANCE_RANGE)
        grade = int(rng.integers(*cfg.PORTFOLIO_GRADE_RANGE))
        base_revenue = rng.uniform(*cfg.PORTFOLIO_REVENUE_RANGE)
        ebitda = base_revenue * rng.uniform(*cfg.PORTFOLIO_MARGIN_RANGE)
        base_debt = ebitda * rng.uniform(*cfg.PORTFOLIO_DEBT_MULTIPLE_RANGE)
        base_dscr = rng.uniform(*cfg.PORTFOLIO_BASE_DSCR_RANGE)
        base_ltv = rng.uniform(*cfg.PORTFOLIO_LTV_RANGE)
        base_ar = synthetic_aging(cfg.SEED + number)
        inventory = pd.DataFrame(cfg.INVENTORY_INPUTS)
        for index, quarter in enumerate(quarters):
            prior = grade
            if index:
                grade = int(np.clip(grade + rng.choice(cfg.PORTFOLIO_GRADE_MOVES,
                                                      p=cfg.PORTFOLIO_GRADE_PROBS),
                                    cfg.GRADE_FLOOR, cfg.GRADE_CEILING))
            balance = base_balance * (1 - cfg.PORTFOLIO_BALANCE_DECAY) ** index
            row = {C.LOAN_ID: f"L{number + 1:03d}", C.LOAN_TYPE: loan_type,
                   C.PROPERTY_TYPE: property_type, C.INDUSTRY: industry, C.QUARTER: str(quarter),
                   C.BALANCE: balance, C.GRADE: grade, C.PRIOR_GRADE: prior, C.CHANGE: grade - prior,
                   C.DSCR: np.nan, C.AVAILABILITY: np.nan, C.COMMITMENT: np.nan,
                   C.SHORTFALL: 0.0, C.SUPERVISORY_FLAG: False, C.BREACH: False,
                   C.LEVERAGE: np.nan, C.FCCR: np.nan, C.NOI: np.nan, C.LTV: np.nan,
                   C.EBITDA: np.nan, C.DEBT: np.nan, C.PRINCIPAL: np.nan,
                   C.INTEREST: np.nan, C.CAPEX: np.nan, C.TAX: np.nan}
            if loan_type == "corporate":
                ebitda *= max(0, 1 + rng.normal(0, cfg.PORTFOLIO_EBITDA_SHOCK))
                debt = base_debt * (1 - cfg.PORTFOLIO_BALANCE_DECAY) ** index
                interest = debt * cfg.FACILITY_RATE
                principal = debt * cfg.PORTFOLIO_PRINCIPAL_RATE
                capex = base_revenue * cfg.PORTFOLIO_CAPEX_RATE
                tax = base_revenue * cfg.PORTFOLIO_TAX_RATE
                fccr = (ebitda - capex - tax) / (interest + principal)
                row.update(covenant_headroom(debt, ebitda, fccr))
                row.update({C.INTEREST: interest, C.PRINCIPAL: principal, C.CAPEX: capex, C.TAX: tax})
            elif loan_type == "cre":
                noi = base_balance * debt_constant(cfg.CRE_RATE, cfg.CRE_AMORT_YEARS) * base_dscr
                noi *= max(0, 1 + rng.normal(0, cfg.PORTFOLIO_CRE_NOI_SHOCK))
                dscr = noi / (balance * debt_constant(cfg.CRE_RATE, cfg.CRE_AMORT_YEARS))
                ltv = base_ltv * (balance / base_balance)
                category = "construction_commercial_multifamily" if property_type == "construction" else "improved_property"
                limit, flag = supervisory_flag(category, ltv)
                row.update({C.NOI: noi, C.DSCR: dscr, C.LTV: ltv, C.SUPERVISORY_LIMIT: limit,
                            C.SUPERVISORY_FLAG: flag, C.BREACH: dscr < cfg.CRE_DSCR_MIN})
                if property_type == "construction":
                    completion = rng.uniform(*cfg.PORTFOLIO_CONSTRUCTION_COMPLETION)
                    undisbursed = cfg.CONSTRUCTION_COMMITMENT * (1 - completion)
                    remaining_equity = max(0, cfg.CONSTRUCTION_EQUITY - cfg.CONSTRUCTION_EQUITY * completion * 2)
                    cost_complete = (undisbursed + remaining_equity - cfg.PORTFOLIO_CONSTRUCTION_BUFFER
                                     + index * cfg.PORTFOLIO_CONSTRUCTION_OVERRUN / cfg.PORTFOLIO_QUARTERS
                                     + rng.normal(0, cfg.PORTFOLIO_CONSTRUCTION_SHOCK))
                    row.update(loan_in_balance(max(0, cost_complete), undisbursed, remaining_equity))
            else:
                aging = base_ar.copy()
                aging.loc[:, list(cfg.AGING_COLUMNS)] *= cfg.PORTFOLIO_AR_SCALE ** (index / cfg.PORTFOLIO_QUARTERS)
                utilization = rng.uniform(*cfg.PORTFOLIO_ABL_UTILIZATION)
                result, _, _ = certificate(aging, inventory, cfg.ABL_COMMITMENT,
                                            cfg.ABL_COMMITMENT * utilization, cfg.ABL_RESERVES, cfg.ABL_FCCR)
                row.update(result)
                row[C.BALANCE] = result[C.OUTSTANDING]
                row[C.BREACH] = result[C.FCCR_BREACH]
            triggers = watchlist_triggers(row)
            row[C.TRIGGERS] = ";".join(triggers)
            row[C.WATCHLIST] = bool(triggers)
            rows.append(row)
    return pd.DataFrame(rows).sort_values([C.QUARTER, C.LOAN_ID]).reset_index(drop=True)


def migration_matrix(history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = history.sort_values([C.LOAN_ID, C.QUARTER]).copy()
    ordered[C.FROM_GRADE] = ordered.groupby(C.LOAN_ID)[C.GRADE].shift()
    transitions = ordered.loc[ordered[C.FROM_GRADE].notna()]
    counts = pd.crosstab(transitions[C.FROM_GRADE], transitions[C.GRADE]).reindex(
        index=range(cfg.GRADE_FLOOR, cfg.GRADE_CEILING + 1),
        columns=range(cfg.GRADE_FLOOR, cfg.GRADE_CEILING + 1), fill_value=0)
    records = []
    for origin in counts.index:
        total = counts.loc[origin].sum()
        for destination in counts.columns:
            count = int(counts.loc[origin, destination])
            # Empty rows receive an explicit identity convention, not an estimated transition.
            probability = count / total if total else float(origin == destination)
            records.append({C.FROM_GRADE: origin, C.TO_GRADE: destination,
                            C.COUNT: count, C.PROBABILITY: probability})
    probabilities = pd.DataFrame(records)
    return counts, probabilities


def concentration(history: pd.DataFrame, dimension: str) -> pd.DataFrame:
    totals = history.groupby([C.QUARTER, dimension], as_index=False)[C.BALANCE].sum()
    totals[C.SHARE] = totals[C.BALANCE] / totals.groupby(C.QUARTER)[C.BALANCE].transform("sum")
    return totals


def quarterly_summary(history: pd.DataFrame) -> pd.DataFrame:
    result = history.groupby(C.QUARTER).agg(**{
        C.LOAN_COUNT: (C.LOAN_ID, "count"), C.BALANCE: (C.BALANCE, "sum"),
        C.WATCH_COUNT: (C.WATCHLIST, "sum")}).reset_index()
    watched = history.loc[history[C.WATCHLIST]].groupby(C.QUARTER)[C.BALANCE].sum()
    result[C.WATCH_BALANCE] = result[C.QUARTER].map(watched).fillna(0)
    result[C.SHARE] = result[C.WATCH_BALANCE] / result[C.BALANCE]
    return result

"""Construction cash funding, annual DSCR sculpting, and reserve waterfalls."""

from dataclasses import asdict
import math

import numpy as np
import pandas as pd

from . import extension_config as cfg
from .extension_config import X, ProjectTerms


def operating_case() -> pd.DataFrame:
    rows, maintenance = [], 0.0
    for year in range(1, cfg.PROJECT_YEARS + 1):
        growth = (1 + cfg.PROJECT_OPEX_ESCALATION) ** (year - 1)
        generation = (cfg.PROJECT_CAPACITY_MW * cfg.PROJECT_HOURS_PER_YEAR * cfg.PROJECT_CAPACITY_FACTOR
                      * (1 - cfg.PROJECT_DEGRADATION) ** (year - 1))
        price = cfg.PROJECT_ENERGY_PRICE * (1 + cfg.PROJECT_PRICE_ESCALATION) ** (year - 1)
        revenue = generation * price
        opex = cfg.PROJECT_OPEX * growth
        contribution = cfg.PROJECT_MAINTENANCE
        spend = maintenance + contribution if year % cfg.MAINTENANCE_CYCLE == 0 else 0.0
        rows.append({X.YEAR: year, X.ENERGY_MWH: generation, X.POWER_PRICE: price,
                     X.REVENUE: revenue, X.OPEX: opex, X.TAX: cfg.PROJECT_TAX,
                     X.MAINT_OPEN: maintenance, X.MAINT_CONTRIB: contribution,
                     X.MAINT_SPEND: spend, X.MAINT_CLOSE: maintenance + contribution - spend,
                     X.CFADS: revenue - opex - cfg.PROJECT_TAX - contribution})
        maintenance += contribution - spend
    return pd.DataFrame(rows)


def sculpt(cfads, terms: ProjectTerms = cfg.PROJECT) -> tuple[dict, pd.DataFrame]:
    cash = np.asarray(cfads, dtype=float)
    if (cash.ndim != 1 or len(cash) == 0 or not np.isfinite(cash).all() or (cash <= 0).any()
            or not all(math.isfinite(v) for v in asdict(terms).values())
            or terms.rate < 0 or terms.cost <= 0 or terms.target_dscr < 1
            or terms.covenant_dscr <= 0 or not 0 < terms.max_cost_leverage <= 1
            or not 0 <= terms.dsra_years <= 1):
        raise ValueError("Positive finite cash flows and valid project terms are required.")
    periods = np.arange(1, len(cash) + 1)
    capacity = float(np.sum(cash / terms.target_dscr / (1 + terms.rate) ** periods))
    debt = min(capacity, terms.cost * terms.max_cost_leverage)
    service = cash / terms.target_dscr * debt / capacity
    initial_dsra = float(service[0] * terms.dsra_years)
    schedule = reserve_waterfall(cash, service, terms.rate, debt, initial_dsra, terms)
    if (schedule[X.PRINCIPAL] < -cfg.EPSILON).any():
        raise ValueError("Cash profile implies negative amortization, which this model excludes.")
    return {X.CAPACITY: capacity, X.LOAN: debt, X.INITIAL_DSRA: initial_dsra,
            X.BINDING: "dscr" if capacity <= terms.cost * terms.max_cost_leverage else "cost_leverage"}, schedule


def reserve_waterfall(cfads, debt_service, rate, opening_debt, initial_dsra,
                      terms: ProjectTerms = cfg.PROJECT, principal=None) -> pd.DataFrame:
    rows, balance, reserve = [], opening_debt, initial_dsra
    for index, cash in enumerate(cfads):
        interest = balance * rate
        scheduled_principal = (debt_service[index] - interest if principal is None else principal[index])
        service = interest + scheduled_principal
        next_service = debt_service[index + 1] if index + 1 < len(cfads) else 0.0
        target = next_service * terms.dsra_years
        draw = min(reserve, max(0.0, service - cash))
        unpaid = max(0.0, service - cash - draw)
        after_service = max(0.0, cash - service)
        release = max(0.0, reserve - draw - target)
        topup = min(after_service, max(0.0, target - reserve + draw))
        close = reserve - draw + topup - release
        rows.append({X.YEAR: index + 1, X.CFADS: float(cash), X.OPENING: balance,
                     X.INTEREST: interest, X.PRINCIPAL: scheduled_principal,
                     X.SERVICE: service, X.CLOSING: balance - scheduled_principal,
                     X.DSCR: cash / service if service > 0 else np.nan,
                     X.DSRA_OPEN: reserve, X.DSRA_TARGET: target, X.DSRA_DRAW: draw,
                     X.DSRA_TOPUP: topup, X.DSRA_RELEASE: release, X.DSRA_CLOSE: close,
                     X.RESERVE_SHORT: max(0.0, target - close), X.UNPAID: unpaid,
                     X.DISTRIBUTION: after_service - topup + release,
                     X.BREACH: bool(cash < service * terms.covenant_dscr - cfg.EPSILON)})
        balance -= scheduled_principal
        reserve = close
    return pd.DataFrame(rows)


def construction_draws(debt: float, initial_dsra: float, terms: ProjectTerms = cfg.PROJECT,
                       weights=cfg.PROJECT_CAPEX_WEIGHTS) -> pd.DataFrame:
    if (not np.isfinite([debt, initial_dsra, *weights]).all() or not 0 <= debt <= terms.cost
            or initial_dsra < 0 or not weights or min(weights) < 0
            or not math.isclose(sum(weights), 1.0, abs_tol=cfg.EPSILON)):
        raise ValueError("Funding must be finite; weights must be nonnegative and sum to one.")
    rows, balance, equity_left = [], 0.0, terms.cost - debt
    for month, weight in enumerate(weights, start=1):
        spend = terms.cost * weight
        equity_capex = min(equity_left, spend)
        draw = spend - equity_capex
        interest = (balance + draw / 2) * terms.rate / cfg.MONTHS
        dsra_funding = initial_dsra if month == len(weights) else 0.0
        rows.append({X.MONTH: month, X.CAPEX: spend, X.OPENING: balance, X.DRAW: draw,
                     X.IDC: interest, X.INITIAL_DSRA: dsra_funding,
                     X.EQUITY_FUNDED: equity_capex + interest + dsra_funding,
                     X.CLOSING: balance + draw,
                     X.COST: spend + interest + dsra_funding})
        equity_left -= equity_capex
        balance += draw
    return pd.DataFrame(rows)


def sensitivity(operations: pd.DataFrame, schedule: pd.DataFrame,
                terms: ProjectTerms = cfg.PROJECT) -> pd.DataFrame:
    rows = []
    for revenue_change in cfg.REVENUE_STRESSES:
        cash = operations[X.CFADS].to_numpy() + operations[X.REVENUE].to_numpy() * revenue_change
        for rate_change in cfg.RATE_STRESSES:
            services = schedule[X.SERVICE].to_numpy() + schedule[X.OPENING].to_numpy() * rate_change
            stressed = reserve_waterfall(cash, services, terms.rate + rate_change,
                                        schedule.head(1)[X.OPENING].item(),
                                        schedule.head(1)[X.DSRA_OPEN].item(), terms,
                                        schedule[X.PRINCIPAL].to_numpy())
            rows.append({X.REVENUE_CHANGE: revenue_change, X.RATE_CHANGE: rate_change,
                         X.MIN_DSCR: stressed[X.DSCR].min(), X.BREACH: bool(stressed[X.BREACH].any()),
                         X.RESERVE_SHORT: stressed[X.RESERVE_SHORT].max(),
                         X.UNPAID: stressed[X.UNPAID].sum()})
    return pd.DataFrame(rows)


def run_project() -> dict:
    operations = operating_case()
    sizing, debt = sculpt(operations[X.CFADS])
    return {"project_operations": operations, "project_sizing": pd.DataFrame([sizing]),
            "project_debt": debt, "project_construction": construction_draws(sizing[X.LOAN], sizing[X.INITIAL_DSRA]),
            "project_sensitivity": sensitivity(operations, debt)}

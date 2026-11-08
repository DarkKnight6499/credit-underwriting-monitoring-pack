"""Synthetic consumer collateral, fixed-pool concentration caps, and cash draws."""

import math

import numpy as np
import pandas as pd

from . import extension_config as cfg
from .extension_config import WarehouseTerms, X

# CONFIG: required input fields and monthly scenario selection.
POOL_NUMBERS = (X.BALANCE, X.SCORE_INPUT, X.DPD, X.REMAINING, X.APR)
POOL_BOOLS = (X.VERIFIED, X.FRAUD, X.DEFAULT)
STRESS_DELINQUENT_FRACTION = .30


def synthetic_pool(seed=cfg.SEED, count=cfg.WAREHOUSE_LOANS) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({X.LOAN_ID: [f"CL{i:04d}" for i in range(1, count + 1)],
                         X.BALANCE: rng.uniform(*cfg.LOAN_BALANCE_RANGE, count),
                         X.SCORE_INPUT: rng.integers(*cfg.LOAN_SCORE_RANGE, count),
                         X.DPD: rng.choice(cfg.LOAN_DPD_CHOICES, count, p=cfg.LOAN_DPD_PROBS),
                         X.REMAINING: rng.integers(*cfg.LOAN_REMAINING_RANGE, count),
                         X.APR: rng.uniform(*cfg.LOAN_APR_RANGE, count),
                         X.STATE: rng.choice(cfg.LOAN_STATES, count),
                         X.GRADE: rng.choice(cfg.LOAN_GRADES, count),
                         X.VERIFIED: rng.random(count) > cfg.POOL_UNVERIFIED_SHARE,
                         X.FRAUD: rng.random(count) < cfg.POOL_FRAUD_SHARE,
                         X.DEFAULT: rng.random(count) < cfg.POOL_INITIAL_DEFAULT_SHARE})


def eligibility(pool: pd.DataFrame, terms: WarehouseTerms = cfg.WAREHOUSE) -> pd.DataFrame:
    if pool.empty or pool[X.LOAN_ID].isna().any() or pool[X.LOAN_ID].duplicated().any():
        raise ValueError("The pool needs nonempty unique loan IDs.")
    if (not np.isfinite(pool.loc[:, list(POOL_NUMBERS)].to_numpy(dtype=float)).all()
            or (pool.loc[:, list(POOL_NUMBERS)] < 0).any().any()
            or pool[X.STATE].isna().any() or pool[X.GRADE].isna().any()
            or not pool.loc[:, list(POOL_BOOLS)].isin([True, False]).all().all()):
        raise ValueError("Missing, negative, nonfinite, or invalid pool inputs.")
    if (not 0 < terms.state_limit <= 1 or not 0 < terms.grade_c_limit <= 1
            or terms.commitment <= 0 or terms.reserve < 0
            or any(not 0 <= rate <= 1 for _, rate in terms.advances)):
        raise ValueError("Invalid warehouse terms.")
    result = pool.copy()
    advances = dict(terms.advances)
    rows = []
    for row in result.to_dict("records"):
        reasons = []
        for failed, reason in ((row[X.SCORE_INPUT] < terms.min_score, "credit_score"),
                               (row[X.DPD] > terms.max_dpd, "delinquent"),
                               (not 0 < row[X.REMAINING] <= terms.max_remaining, "term"),
                               (not row[X.VERIFIED], "income_unverified"),
                               (row[X.FRAUD], "fraud"), (row[X.DEFAULT], "default"),
                               (row[X.GRADE] not in advances, "unsupported_grade")):
            if failed:
                reasons.append(reason)
        rows.append(";".join(reasons))
    result[X.FLAGS] = rows
    result[X.PRE_ELIGIBLE] = result[X.BALANCE].where(result[X.FLAGS].eq(""), 0.0)
    denominator = result[X.PRE_ELIGIBLE].sum()
    state_total = result.groupby(X.STATE)[X.PRE_ELIGIBLE].transform("sum")
    state_excess = (state_total - denominator * terms.state_limit).clip(lower=0)
    result[X.STATE_EXCESS] = (state_excess * result[X.PRE_ELIGIBLE]
                              / state_total.replace(0, np.nan)).fillna(0)
    after_state = result[X.PRE_ELIGIBLE] - result[X.STATE_EXCESS]
    c_total = after_state.where(result[X.GRADE].eq("C"), 0).sum()
    c_excess = max(0.0, c_total - denominator * terms.grade_c_limit)
    result[X.GRADE_EXCESS] = (after_state / c_total * c_excess).where(
        result[X.GRADE].eq("C"), 0) if c_total else 0.0
    result[X.ADJUSTED] = after_state - result[X.GRADE_EXCESS]
    result[X.RATE] = result[X.GRADE].map(advances).fillna(0)
    result[X.ADVANCE] = result[X.ADJUSTED] * result[X.RATE]
    for metric in (X.STATE_EXCESS, X.GRADE_EXCESS):
        affected = result[metric] > cfg.EPSILON
        result.loc[affected, X.FLAGS] = result.loc[affected, X.FLAGS].map(
            lambda text: ";".join(filter(None, (text, metric))))
    return result


def certificate(pool: pd.DataFrame, outstanding: float, cumulative_default_rate=0.0,
                terms: WarehouseTerms = cfg.WAREHOUSE) -> tuple[dict, pd.DataFrame]:
    if not math.isfinite(outstanding) or outstanding < 0 or not 0 <= cumulative_default_rate <= 1:
        raise ValueError("Invalid outstanding or cumulative default rate.")
    detail = eligibility(pool, terms)
    gross = pool[X.BALANCE].sum()
    if gross <= 0:
        raise ValueError("The collateral pool has no positive balance.")
    delinquency = pool.loc[pool[X.DPD] > terms.max_dpd, X.BALANCE].sum() / gross
    apr = float((pool[X.BALANCE] * pool[X.APR]).sum() / gross)
    breaches = []
    for failed, reason in ((delinquency > terms.max_delinquency, "delinquency"),
                           (cumulative_default_rate > terms.max_cumulative_default, "cumulative_defaults"),
                           (apr < terms.min_apr, "weighted_apr")):
        if failed:
            breaches.append(reason)
    base = float(detail[X.ADVANCE].sum())
    availability = min(terms.commitment, base) - terms.reserve - outstanding
    return {X.BALANCE: gross, X.ELIGIBLE_BALANCE: detail[X.ADJUSTED].sum(),
            X.INELIGIBLE_BALANCE: gross - detail[X.ADJUSTED].sum(),
            X.STATE_EXCESS: detail[X.STATE_EXCESS].sum(), X.GRADE_EXCESS: detail[X.GRADE_EXCESS].sum(),
            X.BASE: base, X.COMMITMENT: terms.commitment, X.RESERVES: terms.reserve,
            X.OUTSTANDING: outstanding, X.AVAILABILITY: availability,
            X.WEIGHTED_APR: apr, X.DELINQUENCY: float(delinquency),
            X.CUM_DEFAULT_RATE: cumulative_default_rate, X.BREACH: bool(breaches),
            X.BLOCK_DRAW: bool(breaches) or availability < -cfg.EPSILON,
            X.FLAGS: ";".join(breaches + (["overadvance"] if availability < -cfg.EPSILON else []))}, detail


def draw_period(pool: pd.DataFrame, opening: float, request: float, principal_cash: float,
                external_cash: float, cumulative_default_rate=0.0,
                terms: WarehouseTerms = cfg.WAREHOUSE) -> tuple[dict, dict, pd.DataFrame]:
    if not np.isfinite([request, principal_cash, external_cash]).all() or min(request, principal_cash, external_cash) < 0:
        raise ValueError("Requests and cash must be finite and nonnegative.")
    before, _ = certificate(pool, opening, cumulative_default_rate, terms)
    collection_paydown = min(opening, principal_cash)
    after_collection = opening - collection_paydown
    mandatory = max(0.0, after_collection - max(0.0, min(before[X.BASE], terms.commitment) - terms.reserve))
    external_paydown = min(after_collection, external_cash)
    after_paydown = after_collection - external_paydown
    capacity = max(0.0, min(before[X.BASE], terms.commitment) - terms.reserve - after_paydown)
    draw = 0.0 if before[X.BREACH] or mandatory > external_paydown + cfg.EPSILON else min(request, capacity)
    closing = after_paydown + draw
    final, detail = certificate(pool, closing, cumulative_default_rate, terms)
    log = {X.OPENING: opening, X.REQUEST: request, X.DRAW: draw,
           X.POOL_COLLECTIONS: principal_cash, X.COLLECTION_PAYDOWN: collection_paydown,
           X.MANDATORY_PAYDOWN: mandatory, X.REQUESTED_PAYDOWN: external_cash,
           X.PAYDOWN: collection_paydown + external_paydown,
           X.CASH_SHORT: max(0.0, mandatory - external_paydown), X.OUTSTANDING: closing,
           X.BLOCK_DRAW: before[X.BREACH] or mandatory > external_paydown + cfg.EPSILON}
    return final, log, detail


def run_warehouse() -> dict:
    initial = synthetic_pool()
    pool = initial.copy()
    original_balance = pool[X.BALANCE].sum()
    outstanding, cumulative_losses = cfg.WAREHOUSE.opening, 0.0
    certificates, logs, details, snapshots = [], [], [], []
    for month in range(1, cfg.WAREHOUSE_MONTHS + 1):
        opening_pool = pool[X.BALANCE].sum()
        principal = pool[X.BALANCE] * cfg.POOL_AMORTIZATION
        loss_rate = cfg.POOL_STRESS_DEFAULT_RATE if month == cfg.POOL_STRESS_MONTH else cfg.POOL_DEFAULT_RATE
        losses = (pool[X.BALANCE] - principal) * loss_rate
        interest = float((pool[X.BALANCE] * pool[X.APR]).sum() / cfg.MONTHS)
        pool[X.BALANCE] -= principal + losses
        pool[X.REMAINING] = (pool[X.REMAINING] - 1).clip(lower=0)
        if month == cfg.POOL_STRESS_MONTH:
            affected = pool.head(int(len(pool) * STRESS_DELINQUENT_FRACTION))[X.LOAN_ID]
            pool.loc[pool[X.LOAN_ID].isin(affected), X.DPD] += cfg.WAREHOUSE.max_dpd + 1
        cumulative_losses += losses.sum()
        cert, log, detail = draw_period(pool, outstanding, cfg.WAREHOUSE_DRAW_REQUEST,
                                       float(principal.sum()), cfg.WAREHOUSE_VOLUNTARY_PAYDOWN,
                                       cumulative_losses / original_balance)
        log.update({X.MONTH: month, X.INTEREST_COLLECTIONS: interest,
                    X.INTEREST: outstanding * cfg.WAREHOUSE.annual_rate / cfg.MONTHS,
                    X.LOSSES: losses.sum(), X.BALANCE: opening_pool, X.CLOSING: pool[X.BALANCE].sum()})
        cert[X.MONTH] = month
        detail[X.MONTH] = month
        snapshot = pool.copy()
        snapshot[X.MONTH] = month
        outstanding = cert[X.OUTSTANDING]
        certificates.append(cert)
        logs.append(log)
        details.append(detail)
        snapshots.append(snapshot)
    return {"warehouse_initial_pool": initial, "warehouse_pool_history": pd.concat(snapshots, ignore_index=True),
            "warehouse_certificates": pd.DataFrame(certificates), "warehouse_draw_log": pd.DataFrame(logs),
            "warehouse_eligibility": pd.concat(details, ignore_index=True)}

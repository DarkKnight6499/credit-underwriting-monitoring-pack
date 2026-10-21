"""Illustrative receivable eligibility waterfall and monthly borrowing bases."""

import numpy as np
import pandas as pd

from . import config as cfg
from .config import C


def eligible_receivables(aging: pd.DataFrame) -> pd.DataFrame:
    if aging[C.CUSTOMER].duplicated().any():
        raise ValueError("AR input must contain one row per customer.")
    if (aging.loc[:, list(cfg.AGING_COLUMNS)] < 0).any().any() or (aging[C.CONTRA] < 0).any():
        raise ValueError("Aging balances and contras must be nonnegative.")
    result = aging.copy()
    result[C.GROSS_AR] = result.loc[:, list(cfg.AGING_COLUMNS)].sum(axis=1)
    past_due_share = result[C.AGE90].div(result[C.GROSS_AR].replace(0, np.nan)).fillna(0)
    result[C.CROSS_AGED] = past_due_share > cfg.CROSS_AGING_THRESHOLD
    excluded = result[C.CROSS_AGED] | result[C.AFFILIATE] | result[C.FOREIGN]
    result[C.PRE_CONCENTRATION] = (result[C.GROSS_AR] - result[C.AGE90] - result[C.CONTRA]).clip(lower=0)
    result.loc[excluded, C.PRE_CONCENTRATION] = 0.0
    # A fixed pre-concentration pool avoids a circular concentration calculation.
    cap = result[C.PRE_CONCENTRATION].sum() * cfg.CONCENTRATION_LIMIT
    result[C.CONCENTRATION_EXCESS] = (result[C.PRE_CONCENTRATION] - cap).clip(lower=0)
    result[C.ELIGIBLE_AR] = result[C.PRE_CONCENTRATION] - result[C.CONCENTRATION_EXCESS]
    result[C.INELIGIBLE_AR] = result[C.GROSS_AR] - result[C.ELIGIBLE_AR]
    flags = []
    for row in result.to_dict("records"):
        reasons = []
        for key, label in ((C.CROSS_AGED, "cross_aged"), (C.AFFILIATE, "affiliate"), (C.FOREIGN, "foreign")):
            if row[key]:
                reasons.append(label)
        if row[C.AGE90] > 0:
            reasons.append("over_90")
        if row[C.CONTRA] > 0:
            reasons.append("contra")
        if row[C.CONCENTRATION_EXCESS] > 0:
            reasons.append("concentration_excess")
        flags.append(";".join(reasons))
    result[C.FLAGS] = flags
    return result


def springing_test(availability: float, commitment: float, fccr: float) -> dict:
    if commitment <= 0:
        raise ValueError("Commitment must be positive.")
    active = bool(availability < cfg.SPRINGING_THRESHOLD * commitment)
    breach = active and (not np.isfinite(fccr) or fccr < cfg.MIN_FCCR)
    return {C.SPRINGING: active, C.FCCR_TESTED: fccr if active else np.nan, C.FCCR_BREACH: breach}


def certificate(aging: pd.DataFrame, inventory: pd.DataFrame, commitment: float,
                outstanding: float, reserves: float, fccr: float) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    if min(outstanding, reserves) < 0:
        raise ValueError("Outstanding and reserves must be nonnegative.")
    ar = eligible_receivables(aging)
    inv = inventory.copy()
    if (inv.loc[:, [C.COST, C.NOLV]] < 0).any().any():
        raise ValueError("Inventory values must be nonnegative.")
    inv[C.ELIGIBLE_COST] = inv[C.COST].where(inv[C.ELIGIBLE], 0.0)
    inv[C.ELIGIBLE_NOLV] = inv[C.NOLV].where(inv[C.ELIGIBLE], 0.0)
    eligible_ar = ar[C.ELIGIBLE_AR].sum()
    ar_advance = eligible_ar * cfg.AR_ADVANCE
    inv_advance = min(inv[C.ELIGIBLE_COST].sum() * cfg.INVENTORY_COST_ADVANCE,
                       inv[C.ELIGIBLE_NOLV].sum() * cfg.INVENTORY_NOLV_ADVANCE)
    base = ar_advance + inv_advance
    availability = min(base, commitment) - outstanding - reserves
    result = {C.GROSS_AR: ar[C.GROSS_AR].sum(), C.ELIGIBLE_AR: eligible_ar,
              C.INELIGIBLE_AR: ar[C.INELIGIBLE_AR].sum(),
              C.CONCENTRATION_EXCESS: ar[C.CONCENTRATION_EXCESS].sum(),
              C.ELIGIBLE_COST: inv[C.ELIGIBLE_COST].sum(), C.ELIGIBLE_NOLV: inv[C.ELIGIBLE_NOLV].sum(),
              C.AR_ADVANCE: ar_advance, C.INVENTORY_ADVANCE: inv_advance, C.BASE: base,
              C.COMMITMENT: commitment, C.OUTSTANDING: outstanding, C.RESERVES: reserves,
              C.AVAILABILITY: availability, C.FCCR: fccr, **springing_test(availability, commitment, fccr)}
    return result, ar, inv


def synthetic_aging(seed=cfg.SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for number in range(1, cfg.ABL_CUSTOMERS + 1):
        customer = f"Customer {number:02d}"
        total = rng.uniform(cfg.ABL_AR_MIN, cfg.ABL_AR_MAX)
        shares = cfg.ABL_CROSS_AGE_SHARES if number == 1 else cfg.ABL_AGE_SHARES
        balances = dict(zip(cfg.AGING_COLUMNS, total * np.asarray(shares)))
        rows.append({C.CUSTOMER: customer, **balances,
                     C.AFFILIATE: customer == cfg.ABL_AFFILIATE_CUSTOMER,
                     C.FOREIGN: customer == cfg.ABL_FOREIGN_CUSTOMER,
                     C.CONTRA: cfg.ABL_CONTRA if number == 2 else 0.0})
    return pd.DataFrame(rows)


def run_monthly() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(cfg.SEED)
    aging = synthetic_aging()
    inventory = pd.DataFrame(cfg.INVENTORY_INPUTS)
    outstanding = cfg.ABL_OPENING
    certificates, logs, exceptions, details = [], [], [], []
    for month in range(1, cfg.ABL_MONTHS + 1):
        if month > 1:
            scale = 1 + cfg.ABL_MONTHLY_GROWTH + rng.normal(0, cfg.ABL_MONTHLY_VOLATILITY)
            aging.loc[:, list(cfg.AGING_COLUMNS)] *= scale
        opening = outstanding
        pre, _, _ = certificate(aging, inventory, cfg.ABL_COMMITMENT, opening,
                                 cfg.ABL_RESERVES, cfg.ABL_FCCR)
        draw = min(cfg.ABL_DRAW, max(0, pre[C.AVAILABILITY]))
        paydown = min(cfg.ABL_PAYDOWN, opening + draw)
        outstanding = opening + draw - paydown
        result, ar, _ = certificate(aging, inventory, cfg.ABL_COMMITMENT, outstanding,
                                    cfg.ABL_RESERVES, cfg.ABL_FCCR)
        certificates.append({C.MONTH: month, **result})
        logs.append({C.MONTH: month, C.OPENING: opening, C.DRAW: draw,
                     C.PAYDOWN: paydown, C.OUTSTANDING: outstanding})
        ar[C.MONTH] = month
        details.append(ar)
        for row in ar.loc[ar[C.FLAGS] != ""].to_dict("records"):
            exceptions.append({C.MONTH: month, C.CUSTOMER: row[C.CUSTOMER], C.FLAGS: row[C.FLAGS],
                               C.INELIGIBLE_AR: row[C.INELIGIBLE_AR]})
        if result[C.FCCR_BREACH] or result[C.AVAILABILITY] < 0:
            exceptions.append({C.MONTH: month, C.CUSTOMER: "FACILITY",
                               C.FLAGS: "springing_fccr_breach" if result[C.FCCR_BREACH] else "overadvance",
                               C.INELIGIBLE_AR: 0.0})
    return (pd.DataFrame(certificates), pd.DataFrame(logs), pd.DataFrame(exceptions),
            pd.concat(details, ignore_index=True), inventory)

"""Offline curve valuation and normalized clean-price trade exception checks."""

from dataclasses import dataclass
from datetime import date
import math

import numpy as np
import pandas as pd

from . import extension_config as cfg
from .extension_config import X

# CONFIG: pricing conventions and synthetic example bonds and trade offsets.
BUMP = .0001
BOND_CASES = (
    {X.SECURITY: "SYN-IG", X.COUPON: .045, X.TENOR: 5., X.FREQUENCY: 2, X.ACCRUED: 0., X.SPREAD: .006, X.CALLABLE: False},
    {X.SECURITY: "SYN-BANK", X.COUPON: .05, X.TENOR: 3., X.FREQUENCY: 2, X.ACCRUED: 0., X.SPREAD: .012, X.CALLABLE: False},
    {X.SECURITY: "SYN-GO", X.COUPON: .035, X.TENOR: 7., X.FREQUENCY: 2, X.ACCRUED: 0., X.SPREAD: -.005, X.CALLABLE: False},
    {X.SECURITY: "SYN-REV", X.COUPON: .04, X.TENOR: 10., X.FREQUENCY: 2, X.ACCRUED: 0., X.SPREAD: -.003, X.CALLABLE: False},
)
TRADE_OFFSETS = (.20, 1.50, -.30, -2.00)
DEMO_VENUES = ("SYNTHETIC TRACE schema", "SYNTHETIC TRACE schema", "SYNTHETIC EMMA schema", "SYNTHETIC EMMA schema")
TRADE_STATUS = "trade_status"


@dataclass(frozen=True)
class ZeroCurve:
    tenors: tuple = cfg.CURVE_TENORS
    rates: tuple = cfg.CURVE_RATES
    as_of: str = cfg.AS_OF

    def __post_init__(self):
        if (len(self.tenors) != len(self.rates) or len(self.tenors) < 2
                or not np.isfinite([*self.tenors, *self.rates]).all()
                or min(self.tenors) <= 0 or any(b <= a for a, b in zip(self.tenors, self.tenors[1:]))):
            raise ValueError("Curve needs finite rates and increasing positive tenors.")
        date.fromisoformat(self.as_of)


def bond_price(bond: dict, curve: ZeroCurve, bump=0.0) -> dict:
    maturity, coupon, frequency = bond[X.TENOR], bond[X.COUPON], bond[X.FREQUENCY]
    accrued, spread = bond[X.ACCRUED], bond[X.SPREAD]
    if (not np.isfinite([maturity, coupon, frequency, accrued, spread, bump]).all()
            or maturity <= 0 or coupon < 0 or frequency not in (1, 2, 4, 12)
            or accrued < 0 or accrued > cfg.PRICE_PAR * coupon / frequency + cfg.EPSILON):
        raise ValueError("Invalid bond terms or accrued interest.")
    if bond.get(X.CALLABLE, False):
        raise ValueError("Callable bond valuation requires an option model.")
    if maturity > max(curve.tenors):
        raise ValueError("Cash flows beyond the curve are unsupported.")
    count = math.ceil(maturity * frequency - cfg.EPSILON)
    times = maturity - np.arange(count - 1, -1, -1) / frequency
    cash = np.full(count, cfg.PRICE_PAR * coupon / frequency)
    cash[-1] += cfg.PRICE_PAR
    zeros = np.interp(times, curve.tenors, curve.rates)
    discounted = cash * np.exp(-(zeros + spread + bump) * times)
    dirty = float(discounted.sum())
    return {X.MODEL_DIRTY: dirty, X.MODEL_CLEAN: dirty - accrued,
            X.DURATION: float((discounted * times).sum() / dirty),
            X.CONVEXITY: float((discounted * times ** 2).sum() / dirty)}


def validate_trades(trades: pd.DataFrame, bonds: pd.DataFrame, curve: ZeroCurve,
                    as_of=cfg.AS_OF, tolerance=cfg.PRICE_TOLERANCE,
                    max_age_days=cfg.MAX_TRADE_AGE_DAYS) -> pd.DataFrame:
    if not math.isfinite(tolerance) or tolerance < 0 or max_age_days < 0:
        raise ValueError("Invalid price tolerance or maximum age.")
    if bonds[X.SECURITY].duplicated().any() or trades[X.SECURITY].duplicated().any():
        raise ValueError("Supply one normalized surviving trade and one bond per security.")
    today = date.fromisoformat(as_of)
    curve_age = (today - date.fromisoformat(curve.as_of)).days
    lookup = bonds.set_index(X.SECURITY).to_dict("index")
    rows = []
    for trade in trades.to_dict("records"):
        reasons = []
        try:
            age = (today - date.fromisoformat(trade[X.TRADE_DATE])).days
            stale = age > max_age_days or age < 0
        except (ValueError, TypeError, KeyError):
            stale = True
        if stale:
            reasons.append("stale_or_invalid_trade_date")
        if not 0 <= curve_age <= max_age_days:
            reasons.append("stale_or_future_curve")
        if trade.get(TRADE_STATUS) != "active":
            reasons.append("cancelled_or_unnormalized_trade")
        price = trade.get(X.TRADE_PRICE)
        if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            reasons.append("missing_or_invalid_price")
        bond = lookup.get(trade[X.SECURITY])
        model = {}
        if bond is None:
            reasons.append("missing_bond")
        else:
            try:
                model = bond_price(bond, curve)
            except ValueError as error:
                reasons.append(str(error))
        difference = float(price - model[X.MODEL_CLEAN]) if model and isinstance(price, (float, int)) and math.isfinite(price) else np.nan
        price_break = bool(abs(difference) > tolerance) if not reasons else None
        rows.append({**trade, **model, X.CURVE_DATE: curve.as_of, X.PRICE_DIFF: difference,
                     X.PRICE_BREAK: price_break, X.STALE: stale,
                     X.STATUS: "review required" if reasons else "break" if price_break else "within tolerance",
                     X.FLAGS: ";".join(reasons)})
    return pd.DataFrame(rows)


def run_prices() -> dict:
    curve = ZeroCurve()
    bonds = pd.DataFrame(BOND_CASES)
    trades = pd.DataFrame([{X.SECURITY: bond[X.SECURITY],
                            X.TRADE_PRICE: bond_price(bond, curve)[X.MODEL_CLEAN] + offset,
                            X.TRADE_DATE: cfg.AS_OF, X.VENUE: venue, TRADE_STATUS: "active",
                            X.SOURCE: cfg.SYNTHETIC}
                           for bond, offset, venue in zip(BOND_CASES, TRADE_OFFSETS, DEMO_VENUES)])
    return {"price_bonds": bonds, "price_trades": trades,
            "price_curve": pd.DataFrame({X.TENOR: curve.tenors, X.RATE: curve.rates}),
            "price_validation": validate_trades(trades, bonds, curve)}

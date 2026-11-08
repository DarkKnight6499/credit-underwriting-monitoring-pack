"""Rule 2a-7 subset for plain fixed-rate instruments and direct US obligations."""

import math

import numpy as np
import pandas as pd

from . import extension_config as cfg
from .extension_config import MoneyMarketRules, X

# CONFIG: supported fund types and externally reviewed classification fields.
FUND_TYPES = ("taxable_national", "tax_exempt_national")
BOOLEAN_FIELDS = (X.USD, X.GOVERNMENT, X.DAILY, X.WEEKLY, X.ILLIQUID, X.SUPPORTED)
DEMO_MARKET_VALUE = 1000000.0
DEMO_TREASURY_SHARE = .50
DEMO_PRIVATE_ISSUERS = 10
DEMO_PRIVATE_MATURITIES = (10, 20, 30, 40, 50, 60, 70, 80, 90, 100)


def security_screen(security: dict, rules: MoneyMarketRules = cfg.MONEY_MARKET) -> dict:
    security = {key: bool(value) if isinstance(value, (bool, np.bool_)) else value
                for key, value in security.items()}
    failures, reviews = [], []
    maturity = security.get(X.MATURITY)
    if not isinstance(maturity, (float, int, np.number)) or not math.isfinite(maturity) or maturity < 0 or int(maturity) != maturity:
        reviews.append("missing_or_invalid_maturity")
    elif maturity > rules.max_maturity:
        failures.append("maturity_over_limit")
    for field in BOOLEAN_FIELDS:
        if not isinstance(security.get(field), (bool, np.bool_)):
            reviews.append(f"missing_or_invalid_{field}")
    if security.get(X.USD) is False:
        failures.append("not_usd")
    if security.get(X.SUPPORTED) is not True:
        reviews.append("complex_instrument_out_of_scope")
    if security.get(X.DAILY) is True and security.get(X.WEEKLY) is not True:
        reviews.append("daily_must_also_be_weekly")
    if security.get(X.GOVERNMENT) is True and (security.get(X.DAILY) is not True or security.get(X.WEEKLY) is not True):
        reviews.append("direct_us_obligation_liquidity_classification")
    if security.get(X.GOVERNMENT) is not True:
        review = security.get(X.CREDIT_REVIEW)
        if review is False:
            failures.append("minimal_credit_risk_review_failed")
        elif review is not True:
            reviews.append("minimal_credit_risk_review_required")
    return {X.STATUS: "fail" if failures else "review required" if reviews else "subset pass",
            X.FLAGS: ";".join(failures + reviews)}


def screen_portfolio(holdings: pd.DataFrame, fund_type="taxable_national",
                     rules: MoneyMarketRules = cfg.MONEY_MARKET) -> tuple[dict, pd.DataFrame]:
    if fund_type not in FUND_TYPES:
        raise ValueError("Only national taxable and national tax-exempt funds are supported.")
    if (holdings.empty or holdings[X.SECURITY].isna().any() or holdings[X.SECURITY].duplicated().any()
            or holdings[X.ISSUER].isna().any()
            or not np.isfinite(holdings[X.MARKET_VALUE]).all()
            or (holdings[X.MARKET_VALUE] <= 0).any()):
        raise ValueError("Unique securities, consolidated issuer groups, and positive market values are required.")
    detail = holdings.copy()
    screens = pd.DataFrame([security_screen(row, rules) for row in detail.to_dict("records")])
    detail[X.STATUS] = screens[X.STATUS].to_numpy()
    detail[X.FLAGS] = screens[X.FLAGS].to_numpy()
    total = detail[X.MARKET_VALUE].sum()
    weights = detail[X.MARKET_VALUE] / total
    valid_maturity = pd.to_numeric(detail[X.MATURITY], errors="coerce")
    maturity_valid = (valid_maturity.notna() & np.isfinite(valid_maturity) & (valid_maturity >= 0)).all()
    wam = float((weights * valid_maturity).sum()) if maturity_valid else np.nan
    private = detail.loc[detail[X.GOVERNMENT].eq(False)]
    issuer = private.groupby(X.ISSUER)[X.MARKET_VALUE].sum() / total
    max_share = float(issuer.max()) if len(issuer) else 0.0
    daily = detail.loc[detail[X.DAILY].eq(True), X.MARKET_VALUE].sum() / total
    weekly = detail.loc[detail[X.WEEKLY].eq(True), X.MARKET_VALUE].sum() / total
    illiquid = detail.loc[detail[X.ILLIQUID].eq(True), X.MARKET_VALUE].sum() / total
    flags = []
    for breached, reason in ((wam > rules.max_wam, "wam"), (wam > rules.max_wal, "wal"),
                             (max_share > rules.max_issuer_share + cfg.EPSILON, "issuer_concentration"),
                             (fund_type != "tax_exempt_national" and daily < rules.min_daily - cfg.EPSILON, "daily_liquidity"),
                             (weekly < rules.min_weekly - cfg.EPSILON, "weekly_liquidity"),
                             (illiquid > rules.max_illiquid + cfg.EPSILON, "illiquid_share")):
        if breached:
            flags.append(reason)
    status = ("fail" if detail[X.STATUS].eq("fail").any() else "review required"
              if flags or detail[X.STATUS].eq("review required").any() else "subset pass")
    detail[X.ISSUER_SHARE] = detail[X.ISSUER].map(issuer).fillna(0)
    return {X.WAM: wam, X.WAL: wam, X.DAILY_SHARE: float(daily), X.WEEKLY_SHARE: float(weekly),
            X.ILLIQUID_SHARE: float(illiquid), X.ISSUER_SHARE: max_share,
            X.STATUS: status, X.FLAGS: ";".join(flags)}, detail


def screen_acquisition(holdings: pd.DataFrame, candidate: dict, fund_type="taxable_national",
                       rules: MoneyMarketRules = cfg.MONEY_MARKET) -> dict:
    post = pd.concat([holdings, pd.DataFrame([candidate])], ignore_index=True)
    summary, detail = screen_portfolio(post, fund_type, rules)
    candidate_share = detail.loc[detail[X.SECURITY].eq(candidate[X.SECURITY]), X.ISSUER_SHARE].item()
    reasons = []
    for breached, reason in ((summary[X.WAM] > rules.max_wam, "wam"),
                             (summary[X.WAL] > rules.max_wal, "wal"),
                             (candidate.get(X.GOVERNMENT) is False and candidate_share > rules.max_issuer_share + cfg.EPSILON, "issuer_concentration"),
                             (candidate.get(X.ILLIQUID) is True and summary[X.ILLIQUID_SHARE] > rules.max_illiquid + cfg.EPSILON, "illiquid_purchase"),
                             (fund_type != "tax_exempt_national" and candidate.get(X.DAILY) is False
                              and summary[X.DAILY_SHARE] < rules.min_daily - cfg.EPSILON, "non_daily_purchase"),
                             (candidate.get(X.WEEKLY) is False and summary[X.WEEKLY_SHARE] < rules.min_weekly - cfg.EPSILON, "non_weekly_purchase")):
        if breached:
            reasons.append(reason)
    statuses = detail[X.STATUS]
    status = ("fail" if reasons or statuses.eq("fail").any() else "review required"
              if statuses.eq("review required").any() else "subset pass")
    return {**summary, X.STATUS: status, X.FLAGS: ";".join(reasons + detail.loc[statuses.ne("subset pass"), X.FLAGS].tolist())}


def demo_holdings() -> pd.DataFrame:
    rows = [{X.SECURITY: "SYN-TBILL", X.ISSUER: "US Treasury", X.MARKET_VALUE: DEMO_MARKET_VALUE * DEMO_TREASURY_SHARE,
             X.MATURITY: 30, X.USD: True, X.GOVERNMENT: True, X.CREDIT_REVIEW: None,
             X.DAILY: True, X.WEEKLY: True, X.ILLIQUID: False, X.SUPPORTED: True}]
    for index, maturity in enumerate(DEMO_PRIVATE_MATURITIES, start=1):
        rows.append({X.SECURITY: f"SYN-CP{index:02d}", X.ISSUER: f"Consolidated issuer {index:02d}",
                     X.MARKET_VALUE: DEMO_MARKET_VALUE * (1 - DEMO_TREASURY_SHARE) / DEMO_PRIVATE_ISSUERS,
                     X.MATURITY: maturity, X.USD: True, X.GOVERNMENT: False, X.CREDIT_REVIEW: True,
                     X.DAILY: False, X.WEEKLY: False, X.ILLIQUID: False, X.SUPPORTED: True})
    return pd.DataFrame(rows)


def run_money_market() -> dict:
    holdings = demo_holdings()
    summary, details = screen_portfolio(holdings)
    return {"money_market_holdings": details, "money_market_summary": pd.DataFrame([summary])}

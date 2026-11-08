"""Rule boundaries, acquisition exceptions, and independent bond arithmetic."""

import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from credit_pack import money_market as mm, price_validation as pv
from credit_pack.extension_config import X


def candidate(**overrides):
    return {**mm.demo_holdings().tail(1).to_dict("records")[0], X.SECURITY: "NEW", X.ISSUER: "NEW",
            X.MARKET_VALUE: 1000, **overrides}


@pytest.mark.parametrize("days,status", ((397, "subset pass"), (398, "fail"), (np.nan, "review required")))
def test_security_maturity_boundary(days, status):
    assert mm.security_screen(candidate(**{X.MATURITY: days}))[X.STATUS] == status


def test_credit_review_and_complex_instruments_never_pass_silently():
    assert mm.security_screen(candidate(**{X.CREDIT_REVIEW: None}))[X.STATUS] == "review required"
    assert mm.security_screen(candidate(**{X.CREDIT_REVIEW: False}))[X.STATUS] == "fail"
    assert mm.security_screen(candidate(**{X.SUPPORTED: False}))[X.STATUS] == "review required"


def test_market_value_weighted_average_and_issuer_aggregation():
    holdings = mm.demo_holdings()
    summary, _ = mm.screen_portfolio(holdings)
    assert summary[X.WAM] == pytest.approx(.5 * 30 + .05 * 550)
    assert summary[X.WAL] == summary[X.WAM]
    assert summary[X.DAILY_SHARE] == .5
    assert summary[X.WEEKLY_SHARE] == .5
    assert summary[X.STATUS] == "subset pass"
    holdings.loc[holdings[X.SECURITY].eq("SYN-CP02"), X.ISSUER] = "Consolidated issuer 01"
    assert "issuer_concentration" in mm.screen_portfolio(holdings)[0][X.FLAGS]


def test_liquidity_acquisition_rule_does_not_require_immediate_threshold_cure():
    holdings = mm.demo_holdings()
    holdings.loc[holdings[X.GOVERNMENT], X.MARKET_VALUE] = 10000
    purchase = candidate(**{X.GOVERNMENT: True, X.DAILY: True, X.WEEKLY: True, X.MATURITY: 1})
    # A liquid purchase can improve a shortfall while still leaving liquidity below minimum.
    result = mm.screen_acquisition(holdings, purchase)
    assert "non_daily_purchase" not in result[X.FLAGS]
    assert "non_weekly_purchase" not in result[X.FLAGS]
    assert "non_weekly_purchase" in mm.screen_acquisition(holdings, candidate())[X.FLAGS]


def test_tax_exempt_daily_liquidity_exemption_and_missing_classification():
    holdings = mm.demo_holdings()
    holdings.loc[holdings[X.GOVERNMENT], X.GOVERNMENT] = False
    holdings[X.DAILY] = False
    holdings[X.CREDIT_REVIEW] = True
    summary, _ = mm.screen_portfolio(holdings, "tax_exempt_national")
    assert "daily_liquidity" not in summary[X.FLAGS]
    holdings[X.DAILY] = None
    assert mm.screen_portfolio(holdings)[0][X.STATUS] == "review required"


def test_zero_coupon_continuous_discount_price_duration_convexity():
    curve = pv.ZeroCurve((1., 10.), (.04, .04))
    bond = {X.COUPON: 0., X.TENOR: 2., X.FREQUENCY: 2, X.ACCRUED: 0., X.SPREAD: .01}
    result = pv.bond_price(bond, curve)
    assert result[X.MODEL_DIRTY] == pytest.approx(100 * math.exp(-.05 * 2))
    assert result[X.DURATION] == pytest.approx(2)
    assert result[X.CONVEXITY] == pytest.approx(4)


def test_coupon_price_and_accrued_clean_dirty_hand_case():
    curve = pv.ZeroCurve((.25, 10.), (0., 0.))
    bond = {X.COUPON: .06, X.TENOR: 1., X.FREQUENCY: 2, X.ACCRUED: 1., X.SPREAD: 0.}
    result = pv.bond_price(bond, curve)
    assert result[X.MODEL_DIRTY] == 106
    assert result[X.MODEL_CLEAN] == 105


def test_price_tolerance_equality_stale_cancel_and_callable():
    bond = {X.SECURITY: "B", X.COUPON: 0., X.TENOR: 1., X.FREQUENCY: 1, X.ACCRUED: 0., X.SPREAD: 0.}
    curve = pv.ZeroCurve((1., 10.), (0., 0.))
    trade = {X.SECURITY: "B", X.TRADE_PRICE: 101., X.TRADE_DATE: curve.as_of, pv.TRADE_STATUS: "active"}
    def validate(record, terms=bond):
        return pv.validate_trades(pd.DataFrame([record]), pd.DataFrame([terms]), curve).to_dict("records")[0]
    assert validate(trade)[X.STATUS] == "within tolerance"
    assert validate({**trade, X.TRADE_PRICE: 101.01})[X.PRICE_BREAK]
    assert validate({**trade, X.TRADE_DATE: "2020-01-01"})[X.PRICE_BREAK] is None
    assert validate({**trade, pv.TRADE_STATUS: "cancelled"})[X.STATUS] == "review required"
    assert validate(trade, {**bond, X.CALLABLE: True})[X.STATUS] == "review required"


def test_interpolation_and_curve_validation():
    curve = pv.ZeroCurve((1., 3.), (.02, .04))
    bond = {X.COUPON: 0., X.TENOR: 2., X.FREQUENCY: 1, X.ACCRUED: 0., X.SPREAD: 0.}
    assert pv.bond_price(bond, curve)[X.MODEL_CLEAN] == pytest.approx(100 * math.exp(-.03 * 2))
    with pytest.raises(ValueError):
        pv.ZeroCurve((3., 1.), (.02, .04))


def test_liquidity_and_illiquidity_equal_boundaries():
    from credit_pack import extension_config as cfg
    rules = replace(cfg.MONEY_MARKET, max_issuer_share=1)
    holdings = pd.DataFrame([
        candidate(**{X.SECURITY: "T", X.ISSUER: "Treasury", X.MARKET_VALUE: 25,
                      X.GOVERNMENT: True, X.DAILY: True, X.WEEKLY: True, X.MATURITY: 30}),
        candidate(**{X.SECURITY: "W", X.ISSUER: "W", X.MARKET_VALUE: 25,
                      X.WEEKLY: True, X.MATURITY: 5}),
        candidate(**{X.SECURITY: "I", X.ISSUER: "I", X.MARKET_VALUE: 5,
                      X.ILLIQUID: True, X.MATURITY: 50}),
        candidate(**{X.SECURITY: "N", X.ISSUER: "N", X.MARKET_VALUE: 45, X.MATURITY: 50}),
    ])
    summary, _ = mm.screen_portfolio(holdings, rules=rules)
    assert summary[X.DAILY_SHARE] == .25
    assert summary[X.WEEKLY_SHARE] == .50
    assert summary[X.ILLIQUID_SHARE] == .05
    assert summary[X.STATUS] == "subset pass"
    holdings.loc[holdings[X.SECURITY].eq("N"), X.ILLIQUID] = True
    assert "illiquid_share" in mm.screen_portfolio(holdings, rules=rules)[0][X.FLAGS]


@pytest.mark.parametrize("maturity,flag", ((60, False), (61, True)))
def test_wam_limit_equality(maturity, flag):
    holdings = mm.demo_holdings()
    holdings[X.MATURITY] = maturity
    assert ("wam" in mm.screen_portfolio(holdings)[0][X.FLAGS]) is flag


def test_treasury_purchase_does_not_test_unrelated_private_issuer_limit():
    holdings = mm.demo_holdings()
    holdings.loc[holdings[X.GOVERNMENT].eq(False), X.ISSUER] = "Single private issuer"
    purchase = candidate(**{X.GOVERNMENT: True, X.DAILY: True, X.WEEKLY: True, X.MATURITY: 1})
    assert "issuer_concentration" not in mm.screen_acquisition(holdings, purchase)[X.FLAGS]

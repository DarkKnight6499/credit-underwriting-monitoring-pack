"""Independent ratio, tax, and recommendation boundary calculations."""

import pytest

from credit_pack import issuer_research as research, muni
from credit_pack.extension_config import X


def test_go_ratios_hand_case():
    result = muni.go_analysis({X.REVENUE: 100, X.OPEX: 95, X.FUND_BALANCE: 20,
                               X.DEBT: 50, X.ASSESSED_VALUE: 1000, X.COLLECTION_RATE: .98})
    assert result[X.FUND_RATIO] == .2
    assert result[X.OPERATING_BALANCE] == .05
    assert result[X.DEBT_REVENUE] == .5
    assert result[X.DEBT_VALUE] == .05


def test_revenue_dscr_break_even_and_cash_days():
    inputs = {X.REVENUE: 100, X.OPEX: 40, X.MAINT_CONTRIB: 10,
              X.SERVICE: 25, X.CASH: 20, X.DSCR_MIN: 1.2}
    result = muni.revenue_analysis(inputs)
    assert result[X.DSCR] == 2
    assert result[X.DAYS_CASH] == 182.5
    assert result[X.BREAK_EVEN] == pytest.approx(.2)
    assert muni.revenue_analysis(inputs, -.21)[X.BREACH]


def test_tax_equivalent_yield_and_taxable_muni():
    result = muni.relative_value(.03, .05, .4)
    assert result[X.TEY] == pytest.approx(.05)
    assert result[X.TEY_SPREAD] == pytest.approx(0)
    assert result[X.MUNI_RATIO] == .6
    assert muni.tax_equivalent_yield(.03, .4, False) == .03
    with pytest.raises(ValueError):
        muni.tax_equivalent_yield(.03, 1)


def test_corporate_metrics_hand_case():
    result = research.metrics("corporate", {X.DEBT_CURRENT: 10, X.DEBT_LONG: 80, X.DEBT_SHORT: 10,
                                             X.OP_INCOME: 40, X.DA: 10, X.CFO: 30, X.CAPEX: 5})
    assert result[X.LEVERAGE] == 2
    assert result[X.FCF_DEBT] == .25


def test_scorecard_boundaries_and_missing_inputs():
    result, factors = research.scorecard("gsib", {X.CET1: .14, X.LCR: 1.25}, .002)
    assert result[X.RECOMMENDATION] == "buy"
    assert factors[X.WEIGHT].sum() == 1
    assert result[X.SCORE_AVG] == 1
    assert research.scorecard("gsib", {X.CET1: .14, X.LCR: 1.25}, 0)[0][X.RECOMMENDATION] == "hold"
    assert research.scorecard("gsib", {X.CET1: .09, X.LCR: 1}, .002)[0][X.RECOMMENDATION] == "sell"
    assert research.scorecard("gsib", {}, .002)[0][X.RECOMMENDATION] == "review required"

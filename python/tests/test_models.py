"""Independent arithmetic, policy boundaries, and model invariants."""

import numpy as np
import pandas as pd
import pytest

from credit_pack import abl, config as cfg, construction, cre, facility, portfolio, rating, ratios
from credit_pack.config import C
from tests import inputs as fixture


def test_cre_three_constraint_hand_calculation():
    result = cre.size_loan(**fixture.CRE_FIXTURE)
    for metric, expected in fixture.CRE_EXPECTED.items():
        assert result[metric] == pytest.approx(expected, rel=1e-10)
    assert result[C.BINDING] == C.YIELD_LOAN


@pytest.mark.parametrize("category,ltv,expected", fixture.SUPERVISORY_CASES)
def test_supervisory_limits(category, ltv, expected):
    assert cre.supervisory_flag(category, ltv)[1] is expected


def test_zero_rate_debt_constant():
    assert cre.debt_constant(0, cfg.CRE_AMORT_YEARS) == pytest.approx(1 / cfg.CRE_AMORT_YEARS)


def test_cre_rejects_nonpositive_noi():
    with pytest.raises(ValueError):
        cre.size_loan(0, cfg.CRE_LTV_LIMIT)


def test_construction_balance_shortfall_and_equity_call():
    result = construction.loan_in_balance(*fixture.BALANCE_FIXTURE)
    assert result[C.SHORTFALL] == fixture.BALANCE_SHORTFALL
    assert result[C.EQUITY_CALL]


def test_retainage_cash_draw():
    assert construction.fund_draw(fixture.DRAW_APPROVED) == fixture.DRAW_EXPECTED


def test_draw_review_caps_uninspected_work_and_line_overrun():
    approved, flags = construction.review_line(fixture.DRAW_APPROVED, 0,
                                               fixture.DRAW_APPROVED * 2, cfg.RETAINAGE)
    assert approved == fixture.DRAW_APPROVED * cfg.RETAINAGE
    assert set(flags) == {"requested_exceeds_inspected_completion", "line_overrun"}


def test_construction_equity_first_and_retainage_obligation():
    draws, balances = construction.run_construction()
    assert (draws[C.FUNDED] == draws[C.EQUITY_FUNDED] + draws[C.LOAN_FUNDED]).all()
    loan_rows = draws.loc[draws[C.LOAN_FUNDED] > 0]
    assert (loan_rows[C.CUM_EQUITY] == cfg.CONSTRUCTION_EQUITY).all()
    assert draws[C.LOAN_FUNDED].sum() <= cfg.CONSTRUCTION_COMMITMENT
    assert draws[C.EQUITY_FUNDED].sum() <= cfg.CONSTRUCTION_EQUITY
    assert draws[C.RETAINED].sum() > 0
    final = balances.tail(1).to_dict("records")[0]
    assert final[C.COST_COMPLETE] >= draws[C.RETAINED].sum()
    assert final[C.EQUITY_CALL]
    assert balances[C.FLAGS].str.contains("interest_reserve_shortfall").any()
    assert balances[C.FLAGS].str.contains("contingency_depleted").any()


def test_borrowing_base_cross_aging_and_concentration(aging):
    result, detail, _ = abl.certificate(aging, pd.DataFrame(fixture.INV_FIXTURE),
                                       fixture.CERT_COMMITMENT, fixture.CERT_OUTSTANDING,
                                       fixture.CERT_RESERVES, fixture.CERT_FCCR)
    for metric, expected in fixture.CERT_EXPECTED.items():
        assert result[metric] == pytest.approx(expected)
    customer = detail.set_index(C.CUSTOMER).loc[fixture.DOUBLED_CUSTOMER]
    assert customer[C.CROSS_AGED]
    assert customer[C.ELIGIBLE_AR] == 0
    assert result[C.SPRINGING] is False


@pytest.mark.parametrize("availability,expected", fixture.SPRINGING_CASES)
def test_springing_fccr_strict_threshold(availability, expected):
    result = abl.springing_test(availability, fixture.CERT_COMMITMENT, fixture.CERT_FCCR)
    assert result[C.SPRINGING] is expected
    assert result[C.FCCR_BREACH] is expected
    assert np.isfinite(result[C.FCCR_TESTED]) == expected


def test_missing_fccr_breaches_when_springing_active():
    assert abl.springing_test(0, fixture.CERT_COMMITMENT, np.nan)[C.FCCR_BREACH]


@pytest.mark.parametrize("flag", (C.AFFILIATE, C.FOREIGN))
def test_affiliate_and_foreign_are_fully_ineligible(aging, flag):
    aging.loc[aging[C.CUSTOMER] == fixture.FILTER_CUSTOMER, flag] = True
    result = abl.eligible_receivables(aging).set_index(C.CUSTOMER)
    assert result.loc[fixture.FILTER_CUSTOMER, C.ELIGIBLE_AR] == 0


def test_contras_do_not_create_negative_eligible_ar(aging):
    aging[C.CONTRA] = fixture.INVALID_FACT_VALUE
    assert abl.eligible_receivables(aging)[C.ELIGIBLE_AR].sum() == 0


def test_cross_aging_equality_does_not_exclude_whole_customer(aging):
    aging.loc[aging[C.CUSTOMER] == fixture.DOUBLED_CUSTOMER, C.CURRENT] = 60
    result = abl.eligible_receivables(aging).set_index(C.CUSTOMER)
    assert not result.loc[fixture.DOUBLED_CUSTOMER, C.CROSS_AGED]
    assert result.loc[fixture.DOUBLED_CUSTOMER, C.ELIGIBLE_AR] > 0


def test_abl_duplicate_customer_rejected(aging):
    with pytest.raises(ValueError):
        abl.eligible_receivables(pd.concat([aging, aging], ignore_index=True))


def test_inventory_ineligible_and_negative_availability_are_visible(aging):
    inventory = pd.DataFrame(fixture.INV_FIXTURE)
    inventory[C.ELIGIBLE] = False
    result, _, _ = abl.certificate(aging, inventory, fixture.CERT_COMMITMENT,
                                  fixture.CERT_COMMITMENT, fixture.CERT_RESERVES, fixture.CERT_FCCR)
    assert result[C.INVENTORY_ADVANCE] == 0
    assert result[C.AVAILABILITY] < 0
    assert result[C.FCCR_BREACH]


def test_monthly_draw_log_reconciles():
    certificates, logs, _, _, _ = abl.run_monthly()
    assert np.allclose(logs[C.OPENING] + logs[C.DRAW] - logs[C.PAYDOWN], logs[C.OUTSTANDING])
    assert np.allclose(certificates[C.OUTSTANDING], logs[C.OUTSTANDING])
    assert np.allclose(logs[C.OPENING].tail(cfg.ABL_MONTHS - 1), logs[C.OUTSTANDING].head(cfg.ABL_MONTHS - 1))


def test_leverage_headroom_and_ebitda_cushion():
    result = facility.covenant_headroom(fixture.COVENANT_DEBT, fixture.COVENANT_EBITDA, cfg.MIN_FCCR)
    assert result[C.LEVERAGE] == fixture.COVENANT_LEVERAGE
    assert result[C.CUSHION] == pytest.approx(fixture.COVENANT_CUSHION)
    assert not result[C.BREACH]


def test_nonpositive_ebitda_never_passes_covenants():
    assert facility.covenant_headroom(fixture.COVENANT_DEBT, 0, cfg.MIN_FCCR)[C.BREACH]


def test_rating_monotone_in_leverage():
    grades = []
    qualitative = cfg.BORROWERS[cfg.TICKERS[0]]["qualitative"]
    for leverage in fixture.LEVERAGE_GRID:
        result, _ = rating.scorecard({**fixture.RATING_FINANCIAL, C.LEVERAGE: leverage}, qualitative)
        grades.append(result[C.GRADE])
    assert grades == sorted(grades)


@pytest.mark.parametrize("metric", tuple(cfg.BANDS))
def test_factor_scores_monotone_and_boundary_policy(metric):
    higher_better, boundaries = cfg.BANDS[metric]
    scores = [rating.band_score(metric, value) for value in boundaries]
    assert scores == sorted(scores, reverse=higher_better)
    for value in boundaries:
        better = value + cfg.TOLERANCE if higher_better else value - cfg.TOLERANCE
        assert rating.band_score(metric, value) == rating.band_score(metric, better)


def test_rating_weights_sum_to_one():
    _, factors = rating.scorecard(fixture.RATING_FINANCIAL, cfg.BORROWERS[cfg.TICKERS[0]]["qualitative"])
    assert factors[C.WEIGHT].sum() == pytest.approx(1)


def test_missing_qualitative_input_rejected():
    with pytest.raises(ValueError):
        rating.scorecard(fixture.RATING_FINANCIAL, {})


def test_migration_rows_sum_to_one_and_transition_count():
    history = portfolio.synthetic_portfolio()
    counts, matrix = portfolio.migration_matrix(history)
    assert np.allclose(matrix.groupby(C.FROM_GRADE)[C.PROBABILITY].sum(), 1)
    assert counts.to_numpy().sum() == cfg.PORTFOLIO_LOANS * (cfg.PORTFOLIO_QUARTERS - 1)


def test_portfolio_unique_loans_and_seed_reproducible():
    first, second = portfolio.synthetic_portfolio(), portfolio.synthetic_portfolio()
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == cfg.PORTFOLIO_LOANS * cfg.PORTFOLIO_QUARTERS
    assert not first.duplicated([C.LOAN_ID, C.QUARTER]).any()
    assert first[C.LOAN_ID].nunique() == cfg.PORTFOLIO_LOANS
    assert first[C.PROPERTY_TYPE].eq("construction").any()
    assert first[C.TRIGGERS].str.contains("construction_out_of_balance").any()


def test_concentrations_sum_to_one():
    history = portfolio.synthetic_portfolio()
    result = portfolio.concentration(history, C.INDUSTRY)
    assert np.allclose(result.groupby(C.QUARTER)[C.SHARE].sum(), 1)


def test_undefined_division_not_zero():
    assert np.isnan(ratios.divide(1, 0))
    assert np.isnan(ratios.divide(1, -1))

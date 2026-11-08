"""Hand-computed collateral and cash waterfall cases."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from credit_pack import extension_config as cfg, warehouse
from credit_pack.extension_config import X


def simple_pool():
    return pd.DataFrame([{X.LOAN_ID: name, X.BALANCE: balance, X.SCORE_INPUT: 700,
                          X.DPD: 0, X.REMAINING: 24, X.APR: .18, X.STATE: state,
                          X.GRADE: grade, X.VERIFIED: True, X.FRAUD: False, X.DEFAULT: False}
                         for name, balance, state, grade in (("one", 60, "CA", "A"),
                                                              ("two", 40, "TX", "C"))])


def test_sequential_concentration_and_grade_advance_hand_case():
    terms = replace(cfg.WAREHOUSE, state_limit=.5, grade_c_limit=.25, reserve=0)
    detail = warehouse.eligibility(simple_pool(), terms)
    assert detail[X.STATE_EXCESS].tolist() == [10, 0]
    assert detail[X.GRADE_EXCESS].tolist() == [0, 15]
    assert detail[X.ADJUSTED].tolist() == [50, 25]
    assert detail[X.ADVANCE].sum() == pytest.approx(50 * .85 + 25 * .70)


@pytest.mark.parametrize("column,value", ((X.DPD, 31), (X.SCORE_INPUT, 639), (X.REMAINING, 61),
                                         (X.VERIFIED, False), (X.FRAUD, True), (X.DEFAULT, True)))
def test_eligibility_exclusions(column, value):
    pool = simple_pool()
    pool.loc[pool[X.LOAN_ID].eq("one"), column] = value
    assert warehouse.eligibility(pool).set_index(X.LOAN_ID).loc["one", X.ADVANCE] == 0


def test_eligibility_equal_boundaries_and_duplicate_rejection():
    pool = simple_pool()
    pool[X.DPD], pool[X.SCORE_INPUT], pool[X.REMAINING] = 30, 640, 60
    assert warehouse.eligibility(pool)[X.PRE_ELIGIBLE].sum() == 100
    with pytest.raises(ValueError):
        warehouse.eligibility(pd.concat([pool, pool]))
    pool[X.BALANCE] = np.nan
    with pytest.raises(ValueError):
        warehouse.eligibility(pool)


def test_draw_cap_and_cash_limited_mandatory_paydown():
    terms = replace(cfg.WAREHOUSE, state_limit=1, grade_c_limit=1, reserve=5, commitment=100)
    cert, log, _ = warehouse.draw_period(simple_pool(), 50, 100, 10, 0, terms=terms)
    assert log[X.DRAW] == pytest.approx(34)
    assert cert[X.OUTSTANDING] == pytest.approx(74)
    assert cert[X.AVAILABILITY] == pytest.approx(0)
    cert, log, _ = warehouse.draw_period(simple_pool(), 90, 100, 2, 3, terms=terms)
    assert log[X.MANDATORY_PAYDOWN] == pytest.approx(14)
    assert log[X.CASH_SHORT] == pytest.approx(11)
    assert log[X.DRAW] == 0
    assert cert[X.AVAILABILITY] == pytest.approx(-11)


def test_covenant_breach_blocks_draw_even_with_headroom():
    pool = simple_pool()
    pool[X.DPD] = 31
    cert, log, _ = warehouse.draw_period(pool, 0, 10, 0, 0)
    assert cert[X.BREACH]
    assert log[X.DRAW] == 0


def test_monthly_pool_and_facility_cash_reconcile_and_seed_is_fixed():
    result = warehouse.run_warehouse()
    log = result["warehouse_draw_log"]
    assert np.allclose(log[X.OPENING] + log[X.DRAW] - log[X.PAYDOWN], log[X.OUTSTANDING])
    assert np.allclose(log[X.BALANCE] - log[X.POOL_COLLECTIONS] - log[X.LOSSES], log[X.CLOSING])
    assert result["warehouse_certificates"][X.BREACH].any()
    pd.testing.assert_frame_equal(warehouse.synthetic_pool(), result["warehouse_initial_pool"])
    assert (log.loc[log[X.BLOCK_DRAW], X.DRAW] == 0).all()

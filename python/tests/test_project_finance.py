"""Hand-computed project cash flows and funding identities."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from credit_pack import extension_config as cfg, project_finance as pf
from credit_pack.extension_config import X


def test_two_year_sculpting_hand_calculation():
    terms = replace(cfg.PROJECT, cost=1000, rate=.10, target_dscr=1.25, max_cost_leverage=1)
    sizing, schedule = pf.sculpt([137.5, 151.25], terms)
    # Debt service 110 and 121 has present values 100 and 100.
    assert sizing[X.CAPACITY] == pytest.approx(200)
    assert schedule[X.INTEREST].tolist() == pytest.approx([20, 11])
    assert schedule[X.PRINCIPAL].tolist() == pytest.approx([90, 110])
    assert schedule[X.DSCR].tolist() == pytest.approx([1.25, 1.25])
    assert schedule.tail(1)[X.CLOSING].item() == pytest.approx(0, abs=1e-9)
    assert schedule.tail(1)[X.DSRA_CLOSE].item() == 0
    assert sizing[X.INITIAL_DSRA] == 55


def test_cost_cap_reduces_service_and_raises_dscr():
    terms = replace(cfg.PROJECT, cost=100, rate=0, target_dscr=1.25, max_cost_leverage=.5)
    sizing, schedule = pf.sculpt([50, 50], terms)
    assert sizing[X.LOAN] == 50
    assert schedule[X.SERVICE].tolist() == [25, 25]
    assert schedule[X.DSCR].tolist() == [2, 2]


def test_reserve_draw_topup_release_and_unpaid():
    result = pf.reserve_waterfall([5, 30, 0], [10, 10, 10], 0, 30, 5)
    assert result[X.DSRA_DRAW].tolist() == [5, 0, 5]
    assert result[X.DSRA_TOPUP].tolist() == [0, 5, 0]
    assert result[X.UNPAID].tolist() == [0, 0, 5]
    assert result[X.DISTRIBUTION].tolist() == [0, 15, 0]


def test_construction_equity_first_and_all_sources_equal_uses():
    terms = replace(cfg.PROJECT, cost=100, rate=.12)
    result = pf.construction_draws(60, 5, terms, (.5, .5))
    assert result[X.DRAW].tolist() == pytest.approx([10, 50])
    assert result[X.IDC].tolist() == pytest.approx([.05, .35])
    assert result[X.EQUITY_FUNDED].sum() == pytest.approx(45.4)
    assert np.allclose(result[X.EQUITY_FUNDED] + result[X.DRAW], result[X.COST])


def test_project_reserves_and_fixed_debt_stress():
    result = pf.run_project()
    debt = result["project_debt"]
    ops = result["project_operations"]
    assert np.allclose(ops[X.MAINT_OPEN] + ops[X.MAINT_CONTRIB] - ops[X.MAINT_SPEND], ops[X.MAINT_CLOSE])
    assert np.allclose(debt[X.DSRA_OPEN] - debt[X.DSRA_DRAW] + debt[X.DSRA_TOPUP] - debt[X.DSRA_RELEASE], debt[X.DSRA_CLOSE])
    assert debt.tail(1)[X.CLOSING].item() == pytest.approx(0, abs=1e-6)
    stress = result["project_sensitivity"]
    assert stress.loc[stress[X.REVENUE_CHANGE] == min(cfg.REVENUE_STRESSES), X.MIN_DSCR].max() < debt[X.DSCR].min()
    pd.testing.assert_frame_equal(pf.run_project()["project_operations"], ops)


@pytest.mark.parametrize("cash", ([], [0], [-1], [float("nan")]))
def test_bad_cash_flows_rejected(cash):
    with pytest.raises(ValueError):
        pf.sculpt(cash)

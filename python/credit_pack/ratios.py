"""Cash-flow, capitalization, liquidity, and working-capital ratios."""

import numpy as np
import pandas as pd

from . import config as cfg
from .config import C


def divide(numerator, denominator):
    """Undefined or nonpositive denominators remain unavailable."""
    if isinstance(denominator, pd.Series):
        return numerator / denominator.where(denominator > 0)
    return numerator / denominator if denominator > 0 else np.nan


def calculate(spread: pd.DataFrame, scheduled_principal: float = cfg.HISTORICAL_PRINCIPAL) -> pd.DataFrame:
    result = spread.sort_values([C.TICKER, C.END]).copy()
    result[C.PRINCIPAL] = scheduled_principal
    result[C.EBITDA] = result[C.OP_INCOME] + result[C.DA]
    result[C.LEVERAGE] = divide(result[C.DEBT], result[C.EBITDA])
    result[C.NET_LEVERAGE] = divide(result[C.DEBT] - result[C.CASH], result[C.EBITDA])
    result[C.COVERAGE] = divide(result[C.EBITDA], result[C.INTEREST])
    result[C.FCCR] = divide(result[C.EBITDA] - result[C.CAPEX] - result[C.TAX],
                            result[C.INTEREST] + result[C.PRINCIPAL])
    result[C.CAPITALIZATION] = divide(result[C.DEBT], result[C.DEBT] + result[C.EQUITY])
    result[C.CURRENT_RATIO] = divide(result[C.CURRENT_ASSETS], result[C.CURRENT_LIABILITIES])
    result[C.GROSS_MARGIN] = divide(result[C.REVENUE] - result[C.COGS], result[C.REVENUE])
    result[C.MARGIN] = divide(result[C.EBITDA], result[C.REVENUE])
    result[C.FCF_DEBT] = divide(result[C.CFO] - result[C.CAPEX], result[C.DEBT])
    for balance, flow, metric in ((C.AR, C.REVENUE, C.DSO), (C.INVENTORY, C.COGS, C.DIO),
                                  (C.AP, C.COGS, C.DPO)):
        prior = result.groupby(C.TICKER)[balance].shift()
        average = (result[balance] + prior) / 2
        result[metric] = divide(average, result[flow]) * cfg.DAYS_IN_YEAR
    result[C.MARGIN_STABILITY] = result.groupby(C.TICKER)[C.MARGIN].transform("std")
    return result

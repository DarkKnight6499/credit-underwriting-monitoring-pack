"""Illustrative scorecard, PD scale, classification mapping, and facility LGD."""

import math

import numpy as np
import pandas as pd

from . import config as cfg
from .config import C


def band_score(metric: str, value: float) -> int:
    if not np.isfinite(value):
        return cfg.GRADE_CEILING
    higher_better, boundaries = cfg.BANDS[metric]
    if higher_better:
        return cfg.GRADE_CEILING - sum(value >= boundary for boundary in boundaries)
    return cfg.GRADE_FLOOR + sum(value > boundary for boundary in boundaries)


def scorecard(financial: dict, qualitative: dict) -> tuple[dict, pd.DataFrame]:
    if set(qualitative) != set(cfg.QUAL_WEIGHTS):
        raise ValueError("All four documented qualitative inputs are required.")
    if any(not cfg.GRADE_FLOOR <= value <= cfg.GRADE_CEILING for value in qualitative.values()):
        raise ValueError("Qualitative scores must be between one and ten.")
    detail = []
    for factor, weight in cfg.QUANT_WEIGHTS.items():
        detail.append({C.FACTOR: factor, C.VALUE: financial[factor],
                       C.FACTOR_SCORE: band_score(factor, financial[factor]), C.WEIGHT: weight * cfg.QUANT_WEIGHT})
    for factor, weight in cfg.QUAL_WEIGHTS.items():
        detail.append({C.FACTOR: factor, C.VALUE: qualitative[factor],
                       C.FACTOR_SCORE: qualitative[factor], C.WEIGHT: weight * cfg.QUAL_WEIGHT})
    weighted = sum(row[C.FACTOR_SCORE] * row[C.WEIGHT] for row in detail)
    grade = min(cfg.GRADE_CEILING, max(cfg.GRADE_FLOOR, math.ceil(weighted - cfg.TOLERANCE)))
    if financial[C.EBITDA] <= 0:
        grade = max(grade, cfg.CONDITIONAL_MAX_GRADE + 1)
    result = {C.GRADE: grade, C.SCORE: weighted, C.PD: cfg.PD_SCALE[grade],
              C.CLASSIFICATION: cfg.CLASSIFICATION[grade]}
    return result, pd.DataFrame(detail)


def facility_lgd(seniority: str, collateral: str) -> float:
    return cfg.LGD_TABLE[(seniority, collateral)]

"""Reprice real corporate bonds from reported yields and compare with reported clean prices (WRDS bondret pull, not redistributed)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

# CONFIG: input pull, output summary and column names.
ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "extension" / "raw_wrds" / "bondret_2025-12.csv"
OUTPUT = ROOT / "examples" / "output" / "real_bond_validation.json"
COUPON_COLUMN = "coupon"
YIELD_COLUMN = "yield"
MATURITY_COLUMN = "maturity"
SETTLE_COLUMN = "date"
PRICE_COLUMN = "price_eom"
ISSUER_COLUMN = "company_symbol"
FREQUENCY = 2
PAR = 100.0
BREAK_TOLERANCE = 0.10


def days_30_360(start, end):
    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + min(end.day, 30) - min(start.day, 30)


def clean_price(coupon, yld, maturity, settle):
    schedule, node = [], maturity
    while node > settle:
        schedule.append(node)
        node -= relativedelta(months=12 // FREQUENCY)
    schedule.sort()
    period = 360 // FREQUENCY
    accrued = coupon / FREQUENCY * days_30_360(node, settle) / period
    stub = days_30_360(settle, schedule[0]) / period
    pay = coupon / FREQUENCY
    dirty = sum(pay / (1 + yld / FREQUENCY) ** (stub + i) for i in range(len(schedule)))
    dirty += PAR / (1 + yld / FREQUENCY) ** (stub + len(schedule) - 1)
    return dirty - accrued


def main():
    bonds = pd.read_csv(INPUT, parse_dates=[MATURITY_COLUMN, SETTLE_COLUMN])
    bonds = bonds.dropna(subset=[COUPON_COLUMN, YIELD_COLUMN, PRICE_COLUMN])
    bonds["model"] = [clean_price(c, y, m, s) for c, y, m, s in
                      zip(bonds[COUPON_COLUMN], bonds[YIELD_COLUMN], bonds[MATURITY_COLUMN], bonds[SETTLE_COLUMN])]
    error = (bonds["model"] - bonds[PRICE_COLUMN]).abs()
    summary = {
        "source": "WRDS wrdsapps_bondret.bondret, month-end 2025-12-31, senior fixed-coupon CDEB/CMTN, trade in December 2025",
        "bonds": int(len(bonds)),
        "issuers": int(bonds[ISSUER_COLUMN].nunique()),
        "median_abs_error_points": round(float(error.median()), 4),
        "p95_abs_error_points": round(float(error.quantile(.95)), 4),
        "max_abs_error_points": round(float(error.max()), 4),
        "breaks_over_tolerance": int((error > BREAK_TOLERANCE).sum()),
        "tolerance_points": BREAK_TOLERANCE,
        "convention": "semiannual, 30/360 accrued, settlement at month-end; yield and price from the same record",
        "note": "Raw WRDS rows are licensed and not committed; rerun with your own pull.",
    }
    OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

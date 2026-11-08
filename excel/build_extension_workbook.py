"""Plain formula schedules using the existing workbook conventions."""

from dataclasses import asdict
from datetime import date
import math
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

from credit_pack import extension_config as cfg, money_market as mm, price_validation as pv, warehouse
from credit_pack.extension_config import X
from .build_workbook import DATA_ROW, HEADER_ROW, address, recalculate, schedule

# CONFIG: layout, display formats, and helper fields. Financial terms live in extension_config.
POTENTIAL_SERVICE = "capacity_debt_service"
PV_SERVICE = "present_value_service"
STATE_TOTAL = "state_eligible_total"
POOL_TOTAL = "pool_pre_concentration"
AFTER_STATE = "after_state_deduction"
C_TOTAL = "grade_c_total"
PREVIOUS_POOL = "opening_pool_balance"
LOSS_RATE = "period_loss_rate"
EXTERNAL_PAYDOWN = "external_paydown"
POST_COLLECTION = "debt_after_collection"
CAPACITY = "drawing_capacity"
GROSS_INTEREST = "gross_interest_cash"
TIME = "payment_time_years"
PAYMENT = "payment_amount"
ZERO = "continuous_zero_rate"
DISCOUNTED = "discounted_cash_flow"
WEIGHTED_TIME = "discounted_time"
WEIGHTED_SQUARE = "discounted_time_squared"
LOWER = "lower_curve_index"
SIZING_CELLS = {X.CAPACITY: "P5", X.LOAN: "P6", X.INITIAL_DSRA: "P7"}
PROJECT_CASH_COLUMNS = (X.YEAR, X.ENERGY_MWH, X.POWER_PRICE, X.REVENUE, X.OPEX, X.TAX, X.MAINT_OPEN, X.MAINT_CONTRIB,
                        X.MAINT_SPEND, X.MAINT_CLOSE, X.CFADS, POTENTIAL_SERVICE, PV_SERVICE)
PROJECT_DEBT_COLUMNS = (X.YEAR, X.CFADS, X.OPENING, X.INTEREST, X.PRINCIPAL, X.SERVICE,
                        X.CLOSING, X.DSCR, X.DSRA_OPEN, X.DSRA_TARGET, X.DSRA_DRAW,
                        X.DSRA_TOPUP, X.DSRA_RELEASE, X.DSRA_CLOSE, X.RESERVE_SHORT,
                        X.UNPAID, X.DISTRIBUTION, X.BREACH)
PROJECT_DRAW_COLUMNS = (X.MONTH, X.WEIGHT, X.CAPEX, X.OPENING, X.DRAW, X.IDC, X.INITIAL_DSRA,
                        X.EQUITY_FUNDED, X.CLOSING, X.COST)
POOL_COLUMNS = (X.MONTH, X.LOAN_ID, X.BALANCE, X.SCORE_INPUT, X.DPD, X.REMAINING, X.APR,
                X.STATE, X.GRADE, X.VERIFIED, X.FRAUD, X.DEFAULT, X.PRE_ELIGIBLE,
                POOL_TOTAL, STATE_TOTAL, X.STATE_EXCESS, AFTER_STATE, C_TOTAL,
                X.GRADE_EXCESS, X.ADJUSTED, X.RATE, X.ADVANCE)
CERT_COLUMNS = (X.MONTH, X.BALANCE, X.ELIGIBLE_BALANCE, X.INELIGIBLE_BALANCE,
                X.STATE_EXCESS, X.GRADE_EXCESS, X.BASE, X.COMMITMENT, X.RESERVES,
                X.OUTSTANDING, X.AVAILABILITY, X.WEIGHTED_APR, X.DELINQUENCY,
                X.CUM_DEFAULT_RATE, X.BREACH, X.BLOCK_DRAW)
LOG_COLUMNS = (X.MONTH, PREVIOUS_POOL, LOSS_RATE, X.POOL_COLLECTIONS, X.LOSSES, X.CLOSING,
               X.INTEREST_COLLECTIONS, X.INTEREST, X.OPENING, X.REQUEST, X.REQUESTED_PAYDOWN,
               X.COLLECTION_PAYDOWN, POST_COLLECTION, X.MANDATORY_PAYDOWN, EXTERNAL_PAYDOWN,
               X.CASH_SHORT, CAPACITY, X.BLOCK_DRAW, X.DRAW, X.PAYDOWN, X.OUTSTANDING)
MM_COLUMNS = (X.SECURITY, X.ISSUER, X.MARKET_VALUE, X.MATURITY, X.USD, X.GOVERNMENT,
              X.CREDIT_REVIEW, X.DAILY, X.WEEKLY, X.ILLIQUID, X.SUPPORTED,
              X.ISSUER_SHARE, X.STATUS)
CF_COLUMNS = (X.SECURITY, TIME, PAYMENT, LOWER, ZERO, DISCOUNTED, WEIGHTED_TIME, WEIGHTED_SQUARE)
PRICE_COLUMNS = (X.SECURITY, X.COUPON, X.TENOR, X.FREQUENCY, X.ACCRUED, X.SPREAD, X.CALLABLE,
                 X.TRADE_PRICE, X.TRADE_DATE, X.MODEL_DIRTY, X.MODEL_CLEAN, X.PRICE_DIFF,
                 X.PRICE_BREAK, X.DURATION, X.CONVEXITY, X.CURVE_DATE, pv.TRADE_STATUS, X.STATUS)
RATIO_FIELDS = frozenset((X.DSCR, X.RATE, X.WEIGHTED_APR, X.DELINQUENCY, X.CUM_DEFAULT_RATE,
                          X.ISSUER_SHARE, X.TAX_RATE, X.TEY, X.YIELD, X.TEY_SPREAD, X.MUNI_RATIO,
                          X.REVENUE_CHANGE, X.RATE_CHANGE, X.FUND_RATIO, X.DEBT_VALUE,
                          X.APR, X.COUPON, X.SPREAD, X.TAXABLE_YIELD, X.DAILY_SHARE,
                          X.WEEKLY_SHARE, X.ILLIQUID_SHARE, X.COLLECTION_RATE, ZERO))
INTEGER_FIELDS = frozenset((X.YEAR, X.MONTH, X.SCORE_INPUT, X.DPD, X.REMAINING, X.FREQUENCY,
                            X.MATURITY, LOWER))
BOOLEAN_FIELDS = frozenset((X.STATUS, X.BREACH, X.BLOCK_DRAW, X.PRICE_BREAK, X.CALLABLE,
                            X.VERIFIED, X.FRAUD, X.DEFAULT, X.GOVERNMENT, X.CREDIT_REVIEW,
                            X.DAILY, X.WEEKLY, X.ILLIQUID, X.SUPPORTED, X.USD, X.TAX_EXEMPT))


class Builder:
    def __init__(self):
        self.book = Workbook()
        self.book.remove(self.book.active)
        self.book.properties.creator = cfg.base.AUTHOR
        self.book.properties.lastModifiedBy = cfg.base.AUTHOR
        self.book.calculation = CalcProperties(calcId=0, fullCalcOnLoad=True, forceFullCalc=True)
        self.columns = {}
        self.controls = []
        self.parameters = {}

    def add(self, name, columns, records=()):
        sheet = schedule(self.book, name, columns, list(records))
        self.columns[name] = columns
        sheet["A2"] = "USD. Synthetic except public issuer facts. See docs/extension.md."
        return sheet

    def ref(self, name, field, row, absolute=False):
        ref = address(self.columns[name], field, row)
        if absolute:
            letter = get_column_letter(self.columns[name].index(field) + 1)
            ref = f"${letter}${row}"
        return f"'{name}'!{ref}"

    def put(self, name, row, formulas, expected=None):
        for field, formula in formulas.items():
            cell = address(self.columns[name], field, row)
            self.book[name][cell] = "=" + formula
            if expected is not None and field in expected and pd.notna(expected[field]):
                value = expected[field]
                if isinstance(value, np.generic):
                    value = value.item()
                self.controls.append({"sheet": name, "cell": cell, "metric": field, "python": value})

    def p(self, key):
        return f"'Assumptions'!$B${self.parameters[key]}"

    def size(self, metric):
        return f"'Project cash'!${SIZING_CELLS[metric][0]}${SIZING_CELLS[metric][1:]}"


def assumptions(builder):
    values = {**{f"project.{key}": value for key, value in asdict(cfg.PROJECT).items()},
              **{f"warehouse.{key}": value for key, value in asdict(cfg.WAREHOUSE).items() if key != "advances"},
              **{f"rule.{key}": value for key, value in asdict(cfg.MONEY_MARKET).items()},
              **{f"advance.{grade}": rate for grade, rate in cfg.WAREHOUSE.advances},
              "pool.amortization": cfg.POOL_AMORTIZATION, "pool.default_rate": cfg.POOL_DEFAULT_RATE,
              "pool.stress_default": cfg.POOL_STRESS_DEFAULT_RATE, "pool.stress_month": cfg.POOL_STRESS_MONTH,
              "price.tolerance": cfg.PRICE_TOLERANCE, "price.par": cfg.PRICE_PAR,
              "price.as_of": cfg.AS_OF, "price.max_age": cfg.MAX_TRADE_AGE_DAYS,
              "months_per_year": cfg.MONTHS, "days_per_year": cfg.DAYS,
                       "maintenance.cycle": cfg.MAINTENANCE_CYCLE,
                       "project.capacity_mw": cfg.PROJECT_CAPACITY_MW,
                       "project.capacity_factor": cfg.PROJECT_CAPACITY_FACTOR,
                       "project.hours_per_year": cfg.PROJECT_HOURS_PER_YEAR,
                       "project.energy_price": cfg.PROJECT_ENERGY_PRICE,
                       "project.price_escalation": cfg.PROJECT_PRICE_ESCALATION,
                       "project.degradation": cfg.PROJECT_DEGRADATION}
    sheet = builder.add("Assumptions", (X.METRIC, X.VALUE),
                        [{X.METRIC: key, X.VALUE: value} for key, value in values.items()])
    builder.parameters = {key: row for row, key in enumerate(values, start=DATA_ROW)}
    sheet["A2"] = "Illustrative terms. Rule subset: 17 CFR 270.2a-7(a)(11), (d)(1), (d)(3), (d)(4)."


def project_sheets(b, tables):
    ops = tables["project_operations"]
    b.add("Project cash", PROJECT_CASH_COLUMNS, ops.to_dict("records"))
    for row, record in enumerate(ops.to_dict("records"), start=DATA_ROW):
        c = lambda field: b.ref("Project cash", field, row)
        previous = "0" if row == DATA_ROW else b.ref("Project cash", X.MAINT_CLOSE, row - 1)
        b.put("Project cash", row, {
            X.ENERGY_MWH: f"{b.p('project.capacity_mw')}*{b.p('project.capacity_factor')}*{b.p('project.hours_per_year')}*(1-{b.p('project.degradation')})^({c(X.YEAR)}-1)",
            X.POWER_PRICE: f"{b.p('project.energy_price')}*(1+{b.p('project.price_escalation')})^({c(X.YEAR)}-1)",
            X.REVENUE: f"{c(X.ENERGY_MWH)}*{c(X.POWER_PRICE)}",
            X.MAINT_OPEN: previous,
            X.MAINT_SPEND: f"IF(MOD({c(X.YEAR)},{b.p('maintenance.cycle')})=0,{c(X.MAINT_OPEN)}+{c(X.MAINT_CONTRIB)},0)",
            X.MAINT_CLOSE: f"{c(X.MAINT_OPEN)}+{c(X.MAINT_CONTRIB)}-{c(X.MAINT_SPEND)}",
            X.CFADS: f"{c(X.REVENUE)}-{c(X.OPEX)}-{c(X.TAX)}-{c(X.MAINT_CONTRIB)}",
            POTENTIAL_SERVICE: f"{c(X.CFADS)}/{b.p('project.target_dscr')}",
            PV_SERVICE: f"{c(POTENTIAL_SERVICE)}/(1+{b.p('project.rate')})^{c(X.YEAR)}"}, record)
    last = DATA_ROW + len(ops) - 1
    sizing = tables["project_sizing"].to_dict("records")[0]
    sizing_formulas = {X.CAPACITY: f"SUM({b.ref('Project cash', PV_SERVICE, DATA_ROW)}:{b.ref('Project cash', PV_SERVICE, last)})",
                       X.LOAN: f"MIN({b.size(X.CAPACITY)},{b.p('project.cost')}*{b.p('project.max_cost_leverage')})",
                       X.INITIAL_DSRA: f"{b.ref('Project cash', POTENTIAL_SERVICE, DATA_ROW)}*{b.size(X.LOAN)}/{b.size(X.CAPACITY)}*{b.p('project.dsra_years')}"}
    for metric, cell in SIZING_CELLS.items():
        b.book["Project cash"][f"O{cell[1:]}"] = metric
        b.book["Project cash"][cell] = "=" + sizing_formulas[metric]
        b.controls.append({"sheet": "Project cash", "cell": cell, "metric": metric, "python": sizing[metric]})
    debt = tables["project_debt"]
    b.add("Project debt", PROJECT_DEBT_COLUMNS, debt.to_dict("records"))
    for row, record in enumerate(debt.to_dict("records"), start=DATA_ROW):
        c = lambda field: b.ref("Project debt", field, row)
        opening = b.size(X.LOAN) if row == DATA_ROW else b.ref("Project debt", X.CLOSING, row - 1)
        reserve = b.size(X.INITIAL_DSRA) if row == DATA_ROW else b.ref("Project debt", X.DSRA_CLOSE, row - 1)
        target = "0" if row == last else f"{b.ref('Project debt', X.SERVICE, row + 1)}*{b.p('project.dsra_years')}"
        b.put("Project debt", row, {
            X.CFADS: b.ref("Project cash", X.CFADS, row), X.OPENING: opening,
            X.SERVICE: f"{c(X.CFADS)}/{b.p('project.target_dscr')}*{b.size(X.LOAN)}/{b.size(X.CAPACITY)}",
            X.INTEREST: f"{c(X.OPENING)}*{b.p('project.rate')}", X.PRINCIPAL: f"{c(X.SERVICE)}-{c(X.INTEREST)}",
            X.CLOSING: f"{c(X.OPENING)}-{c(X.PRINCIPAL)}", X.DSCR: f"{c(X.CFADS)}/{c(X.SERVICE)}",
            X.DSRA_OPEN: reserve, X.DSRA_TARGET: target,
            X.DSRA_DRAW: f"MIN({c(X.DSRA_OPEN)},MAX(0,{c(X.SERVICE)}-{c(X.CFADS)}))",
            X.UNPAID: f"MAX(0,{c(X.SERVICE)}-{c(X.CFADS)}-{c(X.DSRA_DRAW)})",
            X.DSRA_TOPUP: f"MIN(MAX(0,{c(X.CFADS)}-{c(X.SERVICE)}),MAX(0,{c(X.DSRA_TARGET)}-{c(X.DSRA_OPEN)}+{c(X.DSRA_DRAW)}))",
            X.DSRA_RELEASE: f"MAX(0,{c(X.DSRA_OPEN)}-{c(X.DSRA_DRAW)}-{c(X.DSRA_TARGET)})",
            X.DSRA_CLOSE: f"{c(X.DSRA_OPEN)}-{c(X.DSRA_DRAW)}+{c(X.DSRA_TOPUP)}-{c(X.DSRA_RELEASE)}",
            X.RESERVE_SHORT: f"MAX(0,{c(X.DSRA_TARGET)}-{c(X.DSRA_CLOSE)})",
            X.DISTRIBUTION: f"MAX(0,{c(X.CFADS)}-{c(X.SERVICE)})-{c(X.DSRA_TOPUP)}+{c(X.DSRA_RELEASE)}",
            X.BREACH: f"{c(X.CFADS)}<{c(X.SERVICE)}*{b.p('project.covenant_dscr')}-{cfg.EPSILON}"}, record)
    draws = tables["project_construction"]
    draw_records = [{**record, X.WEIGHT: weight}
                    for record, weight in zip(draws.to_dict("records"), cfg.PROJECT_CAPEX_WEIGHTS)]
    b.add("Project construction", PROJECT_DRAW_COLUMNS, draw_records)
    for row, record in enumerate(draws.to_dict("records"), start=DATA_ROW):
        c = lambda field: b.ref("Project construction", field, row)
        prior = "0" if row == DATA_ROW else f"SUM({b.ref('Project construction', X.CAPEX, DATA_ROW)}:{b.ref('Project construction', X.CAPEX, row - 1)})"
        b.put("Project construction", row, {
            X.CAPEX: f"{c(X.WEIGHT)}*{b.p('project.cost')}",
            X.OPENING: "0" if row == DATA_ROW else b.ref("Project construction", X.CLOSING, row - 1),
            X.DRAW: f"MAX(0,{c(X.CAPEX)}-MAX(0,{b.p('project.cost')}-{b.size(X.LOAN)}-{prior}))",
            X.IDC: f"({c(X.OPENING)}+{c(X.DRAW)}/2)*{b.p('project.rate')}/{b.p('months_per_year')}",
            X.INITIAL_DSRA: b.size(X.INITIAL_DSRA) if row == DATA_ROW + len(draws) - 1 else "0",
            X.EQUITY_FUNDED: f"{c(X.CAPEX)}-{c(X.DRAW)}+{c(X.IDC)}+{c(X.INITIAL_DSRA)}",
            X.CLOSING: f"{c(X.OPENING)}+{c(X.DRAW)}", X.COST: f"{c(X.CAPEX)}+{c(X.IDC)}+{c(X.INITIAL_DSRA)}"}, record)
    stress_columns = (X.REVENUE_CHANGE, X.RATE_CHANGE, X.YEAR, X.CFADS, X.SERVICE, X.DSCR)
    stress = b.add("Project stress", stress_columns)
    summary = b.add("Sensitivity", (X.REVENUE_CHANGE, X.RATE_CHANGE, X.MIN_DSCR, X.BREACH),
                    tables["project_sensitivity"].to_dict("records"))
    for case_index, case in enumerate(tables["project_sensitivity"].to_dict("records")):
        start = DATA_ROW + case_index * len(ops)
        for offset in range(len(ops)):
            row, base_row = start + offset, DATA_ROW + offset
            stress.cell(row, 1, case[X.REVENUE_CHANGE])
            stress.cell(row, 2, case[X.RATE_CHANGE])
            stress.cell(row, 3, offset + 1)
            c = lambda field: b.ref("Project stress", field, row)
            b.put("Project stress", row, {
                X.CFADS: f"{b.ref('Project cash', X.CFADS, base_row)}+{b.ref('Project cash', X.REVENUE, base_row)}*{c(X.REVENUE_CHANGE)}",
                X.SERVICE: f"{b.ref('Project debt', X.SERVICE, base_row)}+{b.ref('Project debt', X.OPENING, base_row)}*{c(X.RATE_CHANGE)}",
                X.DSCR: f"{c(X.CFADS)}/{c(X.SERVICE)}"})
        b.put("Sensitivity", DATA_ROW + case_index, {
            X.MIN_DSCR: f"MIN({b.ref('Project stress', X.DSCR, start)}:{b.ref('Project stress', X.DSCR, start + len(ops) - 1)})",
            X.BREACH: f"{b.ref('Sensitivity', X.MIN_DSCR, DATA_ROW + case_index)}<{b.p('project.covenant_dscr')}"}, case)


def warehouse_sheets(b, tables):
    initial = tables["warehouse_initial_pool"].copy()
    initial[X.MONTH] = 0
    all_pool = pd.concat([initial, tables["warehouse_pool_history"]], ignore_index=True)
    b.add("Consumer pool", POOL_COLUMNS, all_pool.to_dict("records"))
    lookup = {(record[X.MONTH], record[X.LOAN_ID]): row
              for row, record in enumerate(all_pool.to_dict("records"), start=DATA_ROW)}
    month_ranges = {}
    for month, frame in all_pool.groupby(X.MONTH, sort=False):
        row_numbers = [lookup[(month, loan)] for loan in frame[X.LOAN_ID]]
        month_ranges[month] = (min(row_numbers), max(row_numbers))
    stressed = set(initial.head(int(len(initial) * warehouse.STRESS_DELINQUENT_FRACTION))[X.LOAN_ID])
    expected = pd.concat([warehouse.eligibility(initial), tables["warehouse_eligibility"]], ignore_index=True)
    expected[X.MONTH] = all_pool[X.MONTH].to_numpy()
    expected_map = expected.set_index([X.MONTH, X.LOAN_ID]).to_dict("index")
    for row, record in enumerate(all_pool.to_dict("records"), start=DATA_ROW):
        month, loan = record[X.MONTH], record[X.LOAN_ID]
        c = lambda field: b.ref("Consumer pool", field, row)
        first, last = month_ranges[month]
        r = lambda field: f"{b.ref('Consumer pool', field, first)}:{b.ref('Consumer pool', field, last)}"
        if month:
            prev = lookup[(month - 1, loan)]
            loss_rate = f"IF({c(X.MONTH)}={b.p('pool.stress_month')},{b.p('pool.stress_default')},{b.p('pool.default_rate')})"
            raw_formulas = {field: b.ref("Consumer pool", field, prev) for field in
                            (X.SCORE_INPUT, X.APR, X.STATE, X.GRADE, X.VERIFIED, X.FRAUD, X.DEFAULT)}
            raw_formulas.update({X.BALANCE: f"{b.ref('Consumer pool', X.BALANCE, prev)}*(1-{b.p('pool.amortization')})*(1-{loss_rate})",
                                 X.REMAINING: f"MAX(0,{b.ref('Consumer pool', X.REMAINING, prev)}-1)",
                                 X.DPD: f"{b.ref('Consumer pool', X.DPD, prev)}+IF({c(X.MONTH)}={b.p('pool.stress_month')},{b.p('warehouse.max_dpd')}+1,0)" if loan in stressed else b.ref("Consumer pool", X.DPD, prev)})
            b.put("Consumer pool", row, raw_formulas, record)
        grade_rate = f'IF({c(X.GRADE)}="A",{b.p("advance.A")},IF({c(X.GRADE)}="B",{b.p("advance.B")},IF({c(X.GRADE)}="C",{b.p("advance.C")},0)))'
        b.put("Consumer pool", row, {
            X.PRE_ELIGIBLE: f'IF(AND({c(X.SCORE_INPUT)}>={b.p("warehouse.min_score")},{c(X.DPD)}<={b.p("warehouse.max_dpd")},{c(X.REMAINING)}>0,{c(X.REMAINING)}<={b.p("warehouse.max_remaining")},{c(X.VERIFIED)}=TRUE,{c(X.FRAUD)}=FALSE,{c(X.DEFAULT)}=FALSE,OR({c(X.GRADE)}="A",{c(X.GRADE)}="B",{c(X.GRADE)}="C")),{c(X.BALANCE)},0)',
            POOL_TOTAL: f"SUM({r(X.PRE_ELIGIBLE)})",
            STATE_TOTAL: f"SUMIF({r(X.STATE)},{c(X.STATE)},{r(X.PRE_ELIGIBLE)})",
            X.STATE_EXCESS: f"IF({c(STATE_TOTAL)}>0,MAX(0,{c(STATE_TOTAL)}-{c(POOL_TOTAL)}*{b.p('warehouse.state_limit')})*{c(X.PRE_ELIGIBLE)}/{c(STATE_TOTAL)},0)",
            AFTER_STATE: f"{c(X.PRE_ELIGIBLE)}-{c(X.STATE_EXCESS)}",
            C_TOTAL: f'SUMIF({r(X.GRADE)},"C",{r(AFTER_STATE)})',
            X.GRADE_EXCESS: f'IF(AND({c(X.GRADE)}="C",{c(C_TOTAL)}>0),{c(AFTER_STATE)}/{c(C_TOTAL)}*MAX(0,{c(C_TOTAL)}-{c(POOL_TOTAL)}*{b.p("warehouse.grade_c_limit")}),0)',
            X.ADJUSTED: f"{c(AFTER_STATE)}-{c(X.GRADE_EXCESS)}", X.RATE: grade_rate,
            X.ADVANCE: f"{c(X.ADJUSTED)}*{c(X.RATE)}"}, expected_map[(month, loan)])
    certificates = tables["warehouse_certificates"]
    logs = tables["warehouse_draw_log"]
    b.add("Warehouse dashboard", CERT_COLUMNS, certificates.to_dict("records"))
    b.add("Warehouse draws", LOG_COLUMNS, logs.to_dict("records"))
    original_first, original_last = month_ranges[0]
    original_total = f"SUM({b.ref('Consumer pool', X.BALANCE, original_first)}:{b.ref('Consumer pool', X.BALANCE, original_last)})"
    for row, cert in enumerate(certificates.to_dict("records"), start=DATA_ROW):
        month = cert[X.MONTH]
        first, last = month_ranges[month]
        r = lambda field: f"{b.ref('Consumer pool', field, first)}:{b.ref('Consumer pool', field, last)}"
        c = lambda field: b.ref("Warehouse dashboard", field, row)
        d = lambda field: b.ref("Warehouse draws", field, row)
        formulas = {X.BALANCE: f"SUM({r(X.BALANCE)})", X.ELIGIBLE_BALANCE: f"SUM({r(X.ADJUSTED)})",
                    X.INELIGIBLE_BALANCE: f"{c(X.BALANCE)}-{c(X.ELIGIBLE_BALANCE)}",
                    X.STATE_EXCESS: f"SUM({r(X.STATE_EXCESS)})", X.GRADE_EXCESS: f"SUM({r(X.GRADE_EXCESS)})",
                    X.BASE: f"SUM({r(X.ADVANCE)})", X.COMMITMENT: b.p("warehouse.commitment"),
                    X.RESERVES: b.p("warehouse.reserve"), X.OUTSTANDING: d(X.OUTSTANDING),
                    X.AVAILABILITY: f"MIN({c(X.BASE)},{c(X.COMMITMENT)})-{c(X.RESERVES)}-{c(X.OUTSTANDING)}",
                    X.WEIGHTED_APR: f"SUMPRODUCT({r(X.BALANCE)},{r(X.APR)})/{c(X.BALANCE)}",
                    X.DELINQUENCY: f'SUMIF({r(X.DPD)},">"&{b.p("warehouse.max_dpd")},{r(X.BALANCE)})/{c(X.BALANCE)}',
                    X.CUM_DEFAULT_RATE: f"SUM({b.ref('Warehouse draws', X.LOSSES, DATA_ROW)}:{d(X.LOSSES)})/{original_total}",
                    X.BREACH: f"OR({c(X.DELINQUENCY)}>{b.p('warehouse.max_delinquency')},{c(X.CUM_DEFAULT_RATE)}>{b.p('warehouse.max_cumulative_default')},{c(X.WEIGHTED_APR)}<{b.p('warehouse.min_apr')})",
                    X.BLOCK_DRAW: f"OR({c(X.BREACH)},{c(X.AVAILABILITY)}<-{cfg.EPSILON})"}
        b.put("Warehouse dashboard", row, formulas, cert)
        log = logs.loc[logs[X.MONTH].eq(month)].to_dict("records")[0]
        prev_first, prev_last = month_ranges[month - 1]
        prior_balances = f"{b.ref('Consumer pool', X.BALANCE, prev_first)}:{b.ref('Consumer pool', X.BALANCE, prev_last)}"
        prior_aprs = f"{b.ref('Consumer pool', X.APR, prev_first)}:{b.ref('Consumer pool', X.APR, prev_last)}"
        b.put("Warehouse draws", row, {
            PREVIOUS_POOL: f"SUM({prior_balances})", LOSS_RATE: f"IF({d(X.MONTH)}={b.p('pool.stress_month')},{b.p('pool.stress_default')},{b.p('pool.default_rate')})",
            X.POOL_COLLECTIONS: f"{d(PREVIOUS_POOL)}*{b.p('pool.amortization')}",
            X.LOSSES: f"({d(PREVIOUS_POOL)}-{d(X.POOL_COLLECTIONS)})*{d(LOSS_RATE)}",
            X.CLOSING: c(X.BALANCE), X.INTEREST_COLLECTIONS: f"SUMPRODUCT({prior_balances},{prior_aprs})/{b.p('months_per_year')}",
            X.OPENING: b.p("warehouse.opening") if row == DATA_ROW else b.ref("Warehouse draws", X.OUTSTANDING, row - 1),
            X.INTEREST: f"{d(X.OPENING)}*{b.p('warehouse.annual_rate')}/{b.p('months_per_year')}",
            X.COLLECTION_PAYDOWN: f"MIN({d(X.OPENING)},{d(X.POOL_COLLECTIONS)})",
            POST_COLLECTION: f"{d(X.OPENING)}-{d(X.COLLECTION_PAYDOWN)}",
            X.MANDATORY_PAYDOWN: f"MAX(0,{d(POST_COLLECTION)}-MAX(0,MIN({c(X.BASE)},{c(X.COMMITMENT)})-{c(X.RESERVES)}))",
            EXTERNAL_PAYDOWN: f"MIN({d(POST_COLLECTION)},{d(X.REQUESTED_PAYDOWN)})",
            X.CASH_SHORT: f"MAX(0,{d(X.MANDATORY_PAYDOWN)}-{d(EXTERNAL_PAYDOWN)})",
            CAPACITY: f"MAX(0,MIN({c(X.BASE)},{c(X.COMMITMENT)})-{c(X.RESERVES)}-{d(POST_COLLECTION)}+{d(EXTERNAL_PAYDOWN)})",
            X.BLOCK_DRAW: f"OR({c(X.BREACH)},{d(X.MANDATORY_PAYDOWN)}>{d(EXTERNAL_PAYDOWN)}+{cfg.EPSILON})",
            X.DRAW: f"IF({d(X.BLOCK_DRAW)},0,MIN({d(X.REQUEST)},{d(CAPACITY)}))",
            X.PAYDOWN: f"{d(X.COLLECTION_PAYDOWN)}+{d(EXTERNAL_PAYDOWN)}",
            X.OUTSTANDING: f"{d(X.OPENING)}+{d(X.DRAW)}-{d(X.PAYDOWN)}"}, log)


def muni_sheets(b, tables):
    for name, table_key, fields, formulas in (
        ("Muni GO", "muni_go", (X.ISSUER, X.REVENUE, X.OPEX, X.FUND_BALANCE, X.DEBT, X.ASSESSED_VALUE,
                                 X.COLLECTION_RATE, X.FUND_RATIO, X.OPERATING_BALANCE, X.DEBT_REVENUE, X.DEBT_VALUE),
         {X.FUND_RATIO: "{fund}/{revenue}", X.OPERATING_BALANCE: "({revenue}-{opex})/{revenue}",
          X.DEBT_REVENUE: "{debt}/{revenue}", X.DEBT_VALUE: "{debt}/{assessed}"}),
        ("Muni revenue", "muni_revenue", (X.REVENUE_CHANGE, X.REVENUE, X.OPEX, X.MAINT_CONTRIB, X.SERVICE,
                                           X.CASH, X.DSCR_MIN, X.CFADS, X.DSCR, X.DAYS_CASH, X.BREACH),
         {X.CFADS: "{revenue}-{opex}-{maintenance}", X.DSCR: "{cfads}/{service}",
          X.DAYS_CASH: "{cash}*{days}/{opex}", X.BREACH: "{cfads}<{minimum}*{service}"}),
        ("Muni yields", "muni_relative_value", (X.YIELD, X.TAXABLE_YIELD, X.TAX_RATE, X.TAX_EXEMPT,
                                                X.TEY, X.TEY_SPREAD, X.MUNI_RATIO),
         {X.TEY: "IF({exempt},{yield_value}/(1-{tax}),{yield_value})", X.TEY_SPREAD: "{tey}-{taxable}", X.MUNI_RATIO: "{yield_value}/{taxable}"}),
    ):
        b.add(name, fields, tables[table_key].to_dict("records"))
        for row, record in enumerate(tables[table_key].to_dict("records"), start=DATA_ROW):
            aliases = {"fund": X.FUND_BALANCE, "revenue": X.REVENUE, "opex": X.OPEX, "debt": X.DEBT,
                       "assessed": X.ASSESSED_VALUE, "maintenance": X.MAINT_CONTRIB, "service": X.SERVICE,
                       "cash": X.CASH, "cfads": X.CFADS, "minimum": X.DSCR_MIN, "yield_value": X.YIELD,
                       "tax": X.TAX_RATE, "tey": X.TEY, "taxable": X.TAXABLE_YIELD, "exempt": X.TAX_EXEMPT}
            refs = {key: b.ref(name, field, row) for key, field in aliases.items() if field in fields}
            refs["days"] = b.p("days_per_year")
            b.put(name, row, {field: formula.format(**refs) for field, formula in formulas.items()}, record)
    facts = tables["issuer_facts"]
    b.add("Public issuer facts", tuple(facts.columns), facts.to_dict("records"))
    scores = tables["issuer_scorecards"]
    b.add("Issuer scorecards", tuple(scores.columns), scores.to_dict("records"))
    b.book["Issuer scorecards"]["A2"] = "Saved model calls. Re-run Python after editing facts. Public facts, synthetic spreads and score policy."


def money_market_sheets(b, tables):
    holdings = tables["money_market_holdings"]
    b.add("Money market", MM_COLUMNS, holdings.to_dict("records"))
    last = DATA_ROW + len(holdings) - 1
    r = lambda field: f"{b.ref('Money market', field, DATA_ROW)}:{b.ref('Money market', field, last)}"
    for row, record in enumerate(holdings.to_dict("records"), start=DATA_ROW):
        c = lambda field: b.ref("Money market", field, row)
        b.put("Money market", row, {
            X.ISSUER_SHARE: f"IF({c(X.GOVERNMENT)},0,SUMIF({r(X.ISSUER)},{c(X.ISSUER)},{r(X.MARKET_VALUE)})/SUM({r(X.MARKET_VALUE)}))",
            X.STATUS: f'IF(OR({c(X.MATURITY)}>{b.p("rule.max_maturity")},NOT({c(X.USD)}),AND(NOT({c(X.GOVERNMENT)}),{c(X.CREDIT_REVIEW)}=FALSE,ISLOGICAL({c(X.CREDIT_REVIEW)}))),"fail",IF(OR(NOT({c(X.SUPPORTED)}),NOT(ISNUMBER({c(X.MATURITY)})),AND(NOT({c(X.GOVERNMENT)}),NOT(ISLOGICAL({c(X.CREDIT_REVIEW)})))),"review required","subset pass"))'}, record)
    summary = tables["money_market_summary"].to_dict("records")[0]
    fields = (X.WAM, X.WAL, X.DAILY_SHARE, X.WEEKLY_SHARE, X.ILLIQUID_SHARE, X.ISSUER_SHARE, X.STATUS)
    b.add("Fund screen", fields, [summary])
    c = lambda field: b.ref("Fund screen", field, DATA_ROW)
    b.put("Fund screen", DATA_ROW, {
        X.WAM: f"SUMPRODUCT({r(X.MARKET_VALUE)},{r(X.MATURITY)})/SUM({r(X.MARKET_VALUE)})",
        X.WAL: c(X.WAM),
        X.DAILY_SHARE: f"SUMIF({r(X.DAILY)},TRUE,{r(X.MARKET_VALUE)})/SUM({r(X.MARKET_VALUE)})",
        X.WEEKLY_SHARE: f"SUMIF({r(X.WEEKLY)},TRUE,{r(X.MARKET_VALUE)})/SUM({r(X.MARKET_VALUE)})",
        X.ILLIQUID_SHARE: f"SUMIF({r(X.ILLIQUID)},TRUE,{r(X.MARKET_VALUE)})/SUM({r(X.MARKET_VALUE)})",
        X.ISSUER_SHARE: f"MAX({r(X.ISSUER_SHARE)})",
        X.STATUS: f'IF(COUNTIF({r(X.STATUS)},"fail")>0,"fail",IF(OR(COUNTIF({r(X.STATUS)},"review required")>0,{c(X.WAM)}>{b.p("rule.max_wam")},{c(X.WAL)}>{b.p("rule.max_wal")},{c(X.DAILY_SHARE)}<{b.p("rule.min_daily")},{c(X.WEEKLY_SHARE)}<{b.p("rule.min_weekly")},{c(X.ILLIQUID_SHARE)}>{b.p("rule.max_illiquid")},{c(X.ISSUER_SHARE)}>{b.p("rule.max_issuer_share")}+{cfg.EPSILON}),"review required","subset pass"))'}, summary)
    b.book["Fund screen"]["A2"] = "National taxable, fixed-rate subset only. Liquidity flags require review; acquisition rules are in Python."


def price_sheets(b, tables):
    curve = tables["price_curve"]
    b.add("Zero curve", (X.TENOR, X.RATE), curve.to_dict("records"))
    prices = tables["price_validation"].merge(tables["price_bonds"], on=X.SECURITY, validate="one_to_one")
    b.add("Price validation", PRICE_COLUMNS, prices.to_dict("records"))
    b.book["Price validation"]["A2"] = "Synthetic trades. Price per 100. Continuous zeros. Rebuild after tenor/frequency edits."
    b.add("Price cash flows", CF_COLUMNS)
    curve_last = DATA_ROW + len(curve) - 1
    tenors = f"{b.ref('Zero curve', X.TENOR, DATA_ROW)}:{b.ref('Zero curve', X.TENOR, curve_last)}"
    rates = f"{b.ref('Zero curve', X.RATE, DATA_ROW)}:{b.ref('Zero curve', X.RATE, curve_last)}"
    flow_row = DATA_ROW
    for row, record in enumerate(prices.to_dict("records"), start=DATA_ROW):
        p = lambda field: b.ref("Price validation", field, row)
        first = flow_row
        count = math.ceil(record[X.TENOR] * record[X.FREQUENCY] - cfg.EPSILON)
        for index in range(count):
            c = lambda field: b.ref("Price cash flows", field, flow_row)
            b.book["Price cash flows"][address(CF_COLUMNS, X.SECURITY, flow_row)] = record[X.SECURITY]
            b.put("Price cash flows", flow_row, {
                TIME: f"{p(X.TENOR)}-({count - 1 - index})/{p(X.FREQUENCY)}",
                PAYMENT: f"{b.p('price.par')}*{p(X.COUPON)}/{p(X.FREQUENCY)}" + (f"+{b.p('price.par')}" if index == count - 1 else ""),
                LOWER: f"IF({c(TIME)}<=INDEX({tenors},1),1,MIN({len(curve) - 1},MATCH({c(TIME)},{tenors},1)))",
                ZERO: f"IF({c(TIME)}<=INDEX({tenors},1),INDEX({rates},1),INDEX({rates},{c(LOWER)})+({c(TIME)}-INDEX({tenors},{c(LOWER)}))*(INDEX({rates},{c(LOWER)}+1)-INDEX({rates},{c(LOWER)}))/(INDEX({tenors},{c(LOWER)}+1)-INDEX({tenors},{c(LOWER)})))",
                DISCOUNTED: f"{c(PAYMENT)}*EXP(-({c(ZERO)}+{p(X.SPREAD)})*{c(TIME)})",
                WEIGHTED_TIME: f"{c(DISCOUNTED)}*{c(TIME)}", WEIGHTED_SQUARE: f"{c(DISCOUNTED)}*{c(TIME)}^2"})
            flow_row += 1
        sum_flow = lambda field: f"SUM({b.ref('Price cash flows', field, first)}:{b.ref('Price cash flows', field, flow_row - 1)})"
        b.put("Price validation", row, {
            X.MODEL_DIRTY: sum_flow(DISCOUNTED), X.MODEL_CLEAN: f"{p(X.MODEL_DIRTY)}-{p(X.ACCRUED)}",
            X.PRICE_DIFF: f"{p(X.TRADE_PRICE)}-{p(X.MODEL_CLEAN)}",
            X.PRICE_BREAK: f'IF({p(X.STATUS)}="review required","review required",ABS({p(X.PRICE_DIFF)})>{b.p("price.tolerance")})',
            X.STATUS: f'IFERROR(IF(OR({p(X.CALLABLE)},NOT(ISNUMBER({p(X.TRADE_PRICE)})),{p(X.TRADE_PRICE)}<=0,{p(pv.TRADE_STATUS)}<>"active",DATEVALUE({p(X.TRADE_DATE)})>DATEVALUE({b.p("price.as_of")}),DATEVALUE({b.p("price.as_of")})-DATEVALUE({p(X.TRADE_DATE)})>{b.p("price.max_age")},DATEVALUE({p(X.CURVE_DATE)})>DATEVALUE({b.p("price.as_of")}),DATEVALUE({b.p("price.as_of")})-DATEVALUE({p(X.CURVE_DATE)})>{b.p("price.max_age")},{p(X.TENOR)}>MAX({tenors}),{p(X.TENOR)}<=0,ROUNDUP({p(X.TENOR)}*{p(X.FREQUENCY)},0)<>{count}),"review required",IF(ABS({p(X.PRICE_DIFF)})>{b.p("price.tolerance")},"break","within tolerance")),"review required")',
            X.DURATION: f"{sum_flow(WEIGHTED_TIME)}/{p(X.MODEL_DIRTY)}",
            X.CONVEXITY: f"{sum_flow(WEIGHTED_SQUARE)}/{p(X.MODEL_DIRTY)}"}, record)


def finish(b):
    for sheet in b.book:
        sheet.freeze_panes = "C5"
        sheet.sheet_view.showGridLines = False
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.print_title_rows = "1:4"
        sheet.row_dimensions[1].height = 22
        sheet.row_dimensions[2].height = 28
        sheet.row_dimensions[HEADER_ROW].height = 46
        sheet.auto_filter.ref = f"A4:{get_column_letter(len(b.columns[sheet.title]))}{sheet.max_row}"
        for row in sheet:
            for cell in row:
                cell.font = Font(name=cfg.base.DOC_FONT, size=10, bold=cell.row in (1, HEADER_ROW))
                cell.alignment = Alignment(vertical="top", wrap_text=cell.row == HEADER_ROW)
                if cell.row >= DATA_ROW:
                    header = sheet.cell(HEADER_ROW, cell.column).value
                    if isinstance(cell.value, (int, float)) and not isinstance(cell.value, bool) or cell.data_type == "f":
                        cell.number_format = cfg.base.NUMERIC_FORMAT
                    if header in RATIO_FIELDS:
                        cell.number_format = "0.00%" if header != X.DSCR else '0.00"x"'
                    if header in BOOLEAN_FIELDS:
                        cell.number_format = "General"
                    if header in INTEGER_FIELDS:
                        cell.number_format = "0"
                    if header in (X.WAM, X.WAL):
                        cell.number_format = "0.0"
                if cell.row == 1:
                    cell.font = Font(name=cfg.base.DOC_FONT, size=14, bold=True)
        for column in range(1, sheet.max_column + 1):
            header = str(sheet.cell(HEADER_ROW, column).value or "")
            width = min(30, max(17, len(header) + 2))
            if header in (X.ISSUER, X.SECURITY, X.METRIC, X.STATUS):
                width = 32
            if header in ("url", "section", "document", "verification"):
                width = 65
                for row in sheet.iter_rows(min_row=DATA_ROW, min_col=column, max_col=column):
                    row[0].alignment = Alignment(wrap_text=True, vertical="top")
                    sheet.row_dimensions[row[0].row].height = 80
            sheet.column_dimensions[get_column_letter(column)].width = width
        sheet.print_area = f"A1:{get_column_letter(sheet.max_column)}{sheet.max_row}"
    b.book["Assumptions"].column_dimensions["A"].width = 42
    b.book["Project cash"].column_dimensions["O"].width = 24
    b.book["Project cash"].column_dimensions["P"].width = 22
    for row in b.book["Assumptions"].iter_rows(min_row=DATA_ROW):
        fields = {b.book["Assumptions"].cell(HEADER_ROW, cell.column).value: cell for cell in row}
        key = fields[X.METRIC].value
        value_cell = fields[X.VALUE]
        if (key.startswith("advance.") or key.endswith((".rate", ".annual_rate", ".amortization", ".default_rate",
                ".stress_default", ".capacity_factor", ".price_escalation", ".degradation", ".max_cost_leverage",
                ".state_limit", ".grade_c_limit", ".max_delinquency", ".max_cumulative_default", ".min_apr"))
                or key in ("rule.max_issuer_share", "rule.min_daily", "rule.min_weekly", "rule.max_illiquid")):
            value_cell.number_format = "0.00%"
    for row in b.book["Public issuer facts"].iter_rows(min_row=DATA_ROW):
        fields = {b.book["Public issuer facts"].cell(HEADER_ROW, cell.column).value: cell for cell in row}
        unit = fields["unit"].value
        fields[X.VALUE].number_format = "0.00%" if unit == "fraction" else '0.00"x"' if unit == "multiple" else "#,##0"
    b.book["Public issuer facts"].column_dimensions["C"].width = 24


def build(tables, path=cfg.WORKBOOK):
    b = Builder()
    b.add("Dashboard", (X.METRIC, X.VALUE))
    assumptions(b)
    project_sheets(b, tables)
    warehouse_sheets(b, tables)
    muni_sheets(b, tables)
    money_market_sheets(b, tables)
    price_sheets(b, tables)
    latest = DATA_ROW + len(tables["warehouse_certificates"]) - 1
    headlines = {"Project sized debt": b.size(X.LOAN),
                 "Initial DSRA": b.size(X.INITIAL_DSRA),
                 "Base minimum DSCR": f"MIN({b.ref('Project debt', X.DSCR, DATA_ROW)}:{b.ref('Project debt', X.DSCR, DATA_ROW + len(tables['project_debt']) - 1)})",
                 "Latest warehouse availability": b.ref("Warehouse dashboard", X.AVAILABILITY, latest),
                 "Latest warehouse covenant breach": f'IF({b.ref("Warehouse dashboard", X.BREACH, latest)},"Yes","No")',
                 "Money market subset": b.ref("Fund screen", X.STATUS, DATA_ROW),
                 "Synthetic price breaks": "SUM(" + ",".join(f'IF({b.ref("Price validation", X.PRICE_BREAK, row)}=TRUE,1,0)'
                       for row in range(DATA_ROW, DATA_ROW + len(tables["price_validation"]))) + ")",
                 "Price reviews required": "SUM(" + ",".join(f'IF({b.ref("Price validation", X.STATUS, row)}="review required",1,0)'
                       for row in range(DATA_ROW, DATA_ROW + len(tables["price_validation"]))) + ")"}
    for row, (label, formula) in enumerate(headlines.items(), start=DATA_ROW):
        b.book["Dashboard"].cell(row, 1, label)
        b.put("Dashboard", row, {X.VALUE: formula})
    finish(b)
    b.book["Dashboard"].column_dimensions["A"].width = 40
    b.book["Dashboard"].column_dimensions["B"].width = 26
    b.book["Dashboard"]["B9"].number_format = "General"
    b.book["Dashboard"]["B11"].number_format = "0"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    b.book.save(path)
    b.book.close()
    return b.controls


def verify_recalculated(path, controls):
    book = load_workbook(path, data_only=True)
    results = []
    for control in controls:
        actual = book[control["sheet"]][control["cell"]].value
        expected = control["python"]
        if isinstance(expected, (str, bool)):
            passed = actual == expected
        else:
            passed = isinstance(actual, (int, float)) and math.isclose(actual, expected, abs_tol=1e-6, rel_tol=1e-10)
        results.append({**control, "excel": actual, "result": "PASS" if passed else "FAIL"})
    for sheet in book:
        for row in sheet:
            for cell in row:
                if cell.data_type == "e":
                    raise AssertionError(f"Excel formula error: {sheet.title}!{cell.coordinate} = {cell.value}")
    book.close()
    result = pd.DataFrame(results)
    failures = result.loc[result["result"].ne("PASS")]
    if not failures.empty:
        raise AssertionError(f"Workbook mismatch: {failures.head(8).to_dict('records')}")
    return result


def recalculate_and_verify(path, controls, folder):
    recalculated = recalculate(Path(path), Path(folder))
    checks = verify_recalculated(recalculated, controls)
    shutil.copy2(recalculated, path)
    return checks

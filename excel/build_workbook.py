"""Build plain Excel schedules with formulas that reconcile to Python."""

import math
import shutil
import subprocess
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

from credit_pack import config as cfg
from credit_pack.config import C

# CONFIG: workbook layout; financial assumptions live in credit_pack.config.
HEADER_ROW = 4
DATA_ROW = 5
CRE_ROWS = {C.LOAN: 5, C.BINDING: 6, C.VALUE: 7, C.LTV_LOAN: 8, C.DSCR_LOAN: 9,
            C.YIELD_LOAN: 10, C.DEBT_CONSTANT: 11, C.DSCR: 12, C.STRESS_DSCR: 13,
            C.LTV: 14, C.SUPERVISORY_LIMIT: 15, C.SUPERVISORY_FLAG: 16,
            C.NOI: 20, C.CAP_RATE: 21, C.LTV_LIMIT: 22, C.DSCR_MIN: 23,
            C.RATE: 24, C.AMORT_YEARS: 25, C.YIELD_MIN: 26,
            "rate_stress": 27, "noi_stress": 28, C.CATEGORY: 29,
            C.QUANTITY: 30, C.RENT: 31, C.MARKET_RENT: 32, C.VACANCY: 33,
            C.OTHER_INCOME: 34, C.OPEX: 35, C.RESERVES: 36, C.PGI: 37, C.EGI: 38}
DRAW_COLUMNS = (C.MONTH, C.LINE, C.BUDGET, C.COMPLETE, C.REQUEST, C.APPROVED,
                C.RETAINAGE, C.RETAINED, C.FUNDED, C.EQUITY_FUNDED, C.LOAN_FUNDED,
                C.CUM_APPROVED, C.CUM_FUNDED, C.CUM_EQUITY, C.CUM_LOAN,
                C.COMMITMENT, C.EQUITY, C.FLAGS)
BALANCE_COLUMNS = (C.MONTH, C.COST_COMPLETE, C.UNDISBURSED, C.REMAINING_EQUITY,
                   C.SHORTFALL, C.EQUITY_CALL, C.CUM_EQUITY, C.CUM_LOAN,
                   C.CONTINGENCY_LEFT, C.INTEREST_LEFT, C.INTEREST_REQUIRED, C.FLAGS)
AR_COLUMNS = (C.MONTH, C.CUSTOMER, *cfg.AGING_COLUMNS, C.AFFILIATE, C.FOREIGN, C.CONTRA,
              C.GROSS_AR, C.CROSS_AGED, C.PRE_CONCENTRATION, C.CONCENTRATION_EXCESS, C.ELIGIBLE_AR)
CERT_COLUMNS = (C.MONTH, C.GROSS_AR, C.ELIGIBLE_AR, C.CONCENTRATION_EXCESS,
                C.ELIGIBLE_COST, C.ELIGIBLE_NOLV, C.AR_ADVANCE, C.INVENTORY_ADVANCE,
                C.BASE, C.COMMITMENT, C.OPENING, C.DRAW, C.PAYDOWN, C.OUTSTANDING,
                C.RESERVES, C.AVAILABILITY, C.FCCR, C.SPRINGING, C.FCCR_TESTED, C.FCCR_BREACH)
COVENANT_COLUMNS = (C.TICKER, C.DEBT, C.EBITDA, C.FCCR, C.MAX_LEVERAGE, C.MIN_FCCR,
                    C.LEVERAGE, C.LEVERAGE_HEADROOM, C.FCCR_HEADROOM, C.CUSHION,
                    C.LEVERAGE_BREACH, C.FCCR_BREACH)
INV_COLUMNS = (C.CATEGORY, C.COST, C.NOLV, C.ELIGIBLE, C.ELIGIBLE_COST, C.ELIGIBLE_NOLV)
TEXT_OR_BOOLEAN_COLUMNS = frozenset((C.TICKER, C.MONTH, C.LINE, C.CATEGORY, C.CUSTOMER,
                                     C.FLAGS, C.AFFILIATE, C.FOREIGN, C.CROSS_AGED,
                                     C.ELIGIBLE, C.SPRINGING, C.FCCR_TESTED, C.FCCR_BREACH,
                                     C.LEVERAGE_BREACH, C.EQUITY_CALL))
CRE_PERCENT_METRICS = frozenset((C.CAP_RATE, C.LTV_LIMIT, C.RATE, C.YIELD_MIN,
                                 "rate_stress", "noi_stress", C.VACANCY,
                                 C.DEBT_CONSTANT, C.LTV, C.SUPERVISORY_LIMIT))


def address(columns, column: str, row: int, sheet: str | None = None) -> str:
    lookup = {name: get_column_letter(index) for index, name in enumerate(columns, start=1)}
    cell = f"{lookup[column]}{row}"
    return f"'{sheet}'!{cell}" if sheet else cell


def schedule(book: Workbook, name: str, columns, records: list[dict]):
    sheet = book.create_sheet(name)
    sheet["A1"] = name
    sheet["A2"] = "Synthetic data. All policy assumptions are illustrative. USD unless stated."
    for index, column in enumerate(columns, start=1):
        sheet.cell(HEADER_ROW, index, column)
    for row_number, record in enumerate(records, start=DATA_ROW):
        for index, column in enumerate(columns, start=1):
            value = record.get(column)
            if value is not None and not pd.isna(value):
                sheet.cell(row_number, index, value)
    return sheet


def cre_sheet(book: Workbook, properties: pd.DataFrame):
    sheet = book.create_sheet("CRE")
    sheet["A1"] = "CRE sizing"
    sheet["A2"] = "Synthetic rent rolls; illustrative sizing policy. Monthly amortization."
    sheet["A18"] = "Inputs and rent roll"
    for metric, row in CRE_ROWS.items():
        sheet.cell(row, 1, metric)
    for column_number, inputs in enumerate(properties.to_dict("records"), start=2):
        letter = get_column_letter(column_number)
        sheet.cell(HEADER_ROW, column_number, inputs[C.PROPERTY])
        cell = lambda metric: f"{letter}{CRE_ROWS[metric]}"
        for metric in (C.CAP_RATE, C.CATEGORY, C.QUANTITY, C.RENT, C.MARKET_RENT,
                       C.VACANCY, C.OTHER_INCOME, C.OPEX, C.RESERVES):
            sheet[cell(metric)] = inputs[metric]
        for metric, value in ((C.LTV_LIMIT, cfg.CRE_LTV_LIMIT), (C.DSCR_MIN, cfg.CRE_DSCR_MIN),
                              (C.RATE, cfg.CRE_RATE), (C.AMORT_YEARS, cfg.CRE_AMORT_YEARS),
                              (C.YIELD_MIN, cfg.CRE_YIELD_MIN), ("rate_stress", cfg.CRE_RATE_STRESS),
                              ("noi_stress", cfg.CRE_NOI_STRESS)):
            sheet[cell(metric)] = value
        formulas = {
            C.PGI: f"={cell(C.QUANTITY)}*{cell(C.RENT)}",
            C.EGI: f"={cell(C.PGI)}*(1-{cell(C.VACANCY)})+{cell(C.OTHER_INCOME)}",
            C.NOI: f"={cell(C.EGI)}-{cell(C.OPEX)}-{cell(C.RESERVES)}",
            C.VALUE: f"={cell(C.NOI)}/{cell(C.CAP_RATE)}",
            C.DEBT_CONSTANT: f"=IF({cell(C.RATE)}=0,1/{cell(C.AMORT_YEARS)},12*({cell(C.RATE)}/12)/(1-(1+{cell(C.RATE)}/12)^(-12*{cell(C.AMORT_YEARS)})))",
            C.LTV_LOAN: f"={cell(C.LTV_LIMIT)}*{cell(C.VALUE)}",
            C.DSCR_LOAN: f"={cell(C.NOI)}/({cell(C.DSCR_MIN)}*{cell(C.DEBT_CONSTANT)})",
            C.YIELD_LOAN: f"={cell(C.NOI)}/{cell(C.YIELD_MIN)}",
            C.LOAN: f"=MIN({cell(C.LTV_LOAN)}:{cell(C.YIELD_LOAN)})",
            C.BINDING: f'=IF({cell(C.LOAN)}={cell(C.LTV_LOAN)},"{C.LTV_LOAN}",IF({cell(C.LOAN)}={cell(C.DSCR_LOAN)},"{C.DSCR_LOAN}","{C.YIELD_LOAN}"))',
            C.DSCR: f"={cell(C.NOI)}/({cell(C.LOAN)}*{cell(C.DEBT_CONSTANT)})",
            C.STRESS_DSCR: f"={cell(C.NOI)}*(1+{cell('noi_stress')})/({cell(C.LOAN)}*12*(({cell(C.RATE)}+{cell('rate_stress')})/12)/(1-(1+({cell(C.RATE)}+{cell('rate_stress')})/12)^(-12*{cell(C.AMORT_YEARS)})))",
            C.LTV: f"={cell(C.LOAN)}/{cell(C.VALUE)}",
            C.SUPERVISORY_LIMIT: f"=VLOOKUP({cell(C.CATEGORY)},$E$5:$F$10,2,FALSE)",
            C.SUPERVISORY_FLAG: f"=IF(ISNUMBER({cell(C.SUPERVISORY_LIMIT)}),{cell(C.LTV)}>{cell(C.SUPERVISORY_LIMIT)},FALSE)",
        }
        for metric, formula in formulas.items():
            sheet[cell(metric)] = formula
    sheet["A40"] = "Regulatory source: 12 CFR part 208 Appendix C, Supervisory Loan-to-Value Limits."
    sheet["A41"] = cfg.LTV_SOURCE
    sheet.merge_cells("A40:F40")
    sheet.merge_cells("A41:F42")
    sheet["A41"].alignment = Alignment(wrap_text=True, vertical="top")
    sheet.row_dimensions[41].height = cfg.EXCEL_HEADER_HEIGHT
    sheet["E4"] = "Supervisory category"
    sheet["F4"] = "Regulatory LTV limit"
    for row, (category, limit) in enumerate(cfg.SUPERVISORY_LTV.items(), start=DATA_ROW):
        sheet.cell(row, 5, category)
        sheet.cell(row, 6, limit if limit is not None else "not set")
        sheet.cell(row, 6).number_format = cfg.PERCENT_FORMAT
        sheet.row_dimensions[row].height = cfg.EXCEL_LINE_HEIGHT * 2
    sheet.column_dimensions["E"].width = 38
    sheet.column_dimensions["F"].width = 20
    sheet.column_dimensions["A"].width = 34
    sheet.column_dimensions["B"].width = sheet.column_dimensions["C"].width = 25
    return sheet


def construction_sheets(book: Workbook, draws: pd.DataFrame, balances: pd.DataFrame):
    sheet = schedule(book, "Draws", DRAW_COLUMNS, draws.to_dict("records"))
    previous_line, previous_row, final_month = {}, None, {}
    for row, record in enumerate(draws.to_dict("records"), start=DATA_ROW):
        cell = lambda metric, r=row: address(DRAW_COLUMNS, metric, r)
        prior_line = previous_line.get(record[C.LINE])
        previous_approved = cell(C.CUM_APPROVED, prior_line) if prior_line else "0"
        previous_funded = cell(C.CUM_FUNDED, prior_line) if prior_line else "0"
        previous_equity = cell(C.CUM_EQUITY, previous_row) if previous_row else "0"
        previous_loan = cell(C.CUM_LOAN, previous_row) if previous_row else "0"
        sheet[cell(C.COMMITMENT)] = cfg.CONSTRUCTION_COMMITMENT
        sheet[cell(C.EQUITY)] = cfg.CONSTRUCTION_EQUITY
        formulas = {
            C.APPROVED: f"=MAX(0,MIN({cell(C.REQUEST)},{cell(C.BUDGET)}*{cell(C.COMPLETE)}-{previous_approved},{cell(C.BUDGET)}-{previous_approved}))",
            C.RETAINED: f"={cell(C.APPROVED)}*{cell(C.RETAINAGE)}",
            C.EQUITY_FUNDED: f"=MIN({cell(C.APPROVED)}-{cell(C.RETAINED)},MAX(0,{cell(C.EQUITY)}-{previous_equity}))",
            C.LOAN_FUNDED: f"=MIN({cell(C.APPROVED)}-{cell(C.RETAINED)}-{cell(C.EQUITY_FUNDED)},MAX(0,{cell(C.COMMITMENT)}-{previous_loan}))",
            C.FUNDED: f"={cell(C.EQUITY_FUNDED)}+{cell(C.LOAN_FUNDED)}",
            C.CUM_APPROVED: f"={previous_approved}+{cell(C.APPROVED)}",
            C.CUM_FUNDED: f"={previous_funded}+{cell(C.FUNDED)}",
            C.CUM_EQUITY: f"={previous_equity}+{cell(C.EQUITY_FUNDED)}",
            C.CUM_LOAN: f"={previous_loan}+{cell(C.LOAN_FUNDED)}",
            C.FLAGS: f'=IF({previous_approved}+{cell(C.REQUEST)}>{cell(C.BUDGET)}*{cell(C.COMPLETE)}+{cfg.TOLERANCE},"requested_exceeds_inspected_completion;","")&IF({previous_approved}+{cell(C.REQUEST)}>{cell(C.BUDGET)}+{cfg.TOLERANCE},"line_overrun;","")',
        }
        for metric, formula in formulas.items():
            sheet[cell(metric)] = formula
        previous_line[record[C.LINE]] = previous_row = row
        final_month[record[C.MONTH]] = row
    balance_sheet = schedule(book, "Balance", BALANCE_COLUMNS, balances.to_dict("records"))
    for row, record in enumerate(balances.to_dict("records"), start=DATA_ROW):
        cell = lambda metric: address(BALANCE_COLUMNS, metric, row)
        draw_row = final_month[record[C.MONTH]]
        eq = address(DRAW_COLUMNS, C.CUM_EQUITY, draw_row, "Draws")
        loan = address(DRAW_COLUMNS, C.CUM_LOAN, draw_row, "Draws")
        formulas = {
            C.CUM_EQUITY: f"={eq}", C.CUM_LOAN: f"={loan}",
            C.COST_COMPLETE: f"=MAX(0,{sum(cfg.CONSTRUCTION_BUDGET.values())}+{cfg.CONSTRUCTION_BUDGET[cfg.CONSTRUCTION_HARD_LINE]}*{cfg.CONSTRUCTION_OVERRUN}*{cell(C.MONTH)}/{cfg.CONSTRUCTION_MONTHS}-{eq}-{loan})",
            C.UNDISBURSED: f"={cfg.CONSTRUCTION_COMMITMENT}-{loan}",
            C.REMAINING_EQUITY: f"={cfg.CONSTRUCTION_EQUITY}-{eq}",
            C.SHORTFALL: f"=MAX(0,{cell(C.COST_COMPLETE)}-{cell(C.UNDISBURSED)}-{cell(C.REMAINING_EQUITY)})",
            C.EQUITY_CALL: f"={cell(C.SHORTFALL)}>{cfg.TOLERANCE}",
        }
        for metric, formula in formulas.items():
            balance_sheet[cell(metric)] = formula
        draw_end = DATA_ROW + len(draws) - 1
        draw_range = lambda metric: f"'Draws'!{address(DRAW_COLUMNS, metric, DATA_ROW)}:{address(DRAW_COLUMNS, metric, draw_end)}"
        balance_sheet[cell(C.CONTINGENCY_LEFT)] = f"={cfg.CONSTRUCTION_BUDGET[cfg.CONSTRUCTION_CONTINGENCY_LINE]}-{cfg.CONSTRUCTION_CONTINGENCY_USE}*{cell(C.MONTH)}/{cfg.CONSTRUCTION_MONTHS}"
        balance_sheet[cell(C.INTEREST_LEFT)] = f'={cfg.CONSTRUCTION_BUDGET[cfg.CONSTRUCTION_INTEREST_LINE]}-SUMIFS({draw_range(C.FUNDED)},{draw_range(C.LINE)},"{cfg.CONSTRUCTION_INTEREST_LINE}",{draw_range(C.MONTH)},"<="&{cell(C.MONTH)})'
        balance_sheet[cell(C.INTEREST_REQUIRED)] = f"={cfg.CONSTRUCTION_RESERVE_NEED}*(1-{cell(C.MONTH)}/{cfg.CONSTRUCTION_MONTHS})"
        balance_sheet[cell(C.FLAGS)] = f'=IF({cell(C.CONTINGENCY_LEFT)}<={cfg.TOLERANCE},"contingency_depleted;","")&IF({cell(C.INTEREST_LEFT)}+{cfg.TOLERANCE}<{cell(C.INTEREST_REQUIRED)},"interest_reserve_shortfall;","")&IF({cell(C.EQUITY_CALL)},"loan_out_of_balance","")'


def abl_sheets(book: Workbook, details: pd.DataFrame, inventory: pd.DataFrame,
               certificates: pd.DataFrame, logs: pd.DataFrame):
    ar_sheet = schedule(book, "AR eligibility", AR_COLUMNS, details.to_dict("records"))
    last_row = DATA_ROW + len(details) - 1
    ref = lambda column: f"'AR eligibility'!{address(AR_COLUMNS, column, DATA_ROW)}:{address(AR_COLUMNS, column, last_row)}"
    for row in range(DATA_ROW, last_row + 1):
        cell = lambda metric: address(AR_COLUMNS, metric, row)
        formulas = {
            C.GROSS_AR: f"=SUM({cell(C.CURRENT)}:{cell(C.AGE90)})",
            C.CROSS_AGED: f"=IF({cell(C.GROSS_AR)}=0,FALSE,{cell(C.AGE90)}/{cell(C.GROSS_AR)}>{cfg.CROSS_AGING_THRESHOLD})",
            C.PRE_CONCENTRATION: f"=IF(OR({cell(C.CROSS_AGED)},{cell(C.AFFILIATE)},{cell(C.FOREIGN)}),0,MAX(0,{cell(C.GROSS_AR)}-{cell(C.AGE90)}-{cell(C.CONTRA)}))",
            C.CONCENTRATION_EXCESS: f"=MAX(0,{cell(C.PRE_CONCENTRATION)}-{cfg.CONCENTRATION_LIMIT}*SUMIFS({ref(C.PRE_CONCENTRATION)},{ref(C.MONTH)},{cell(C.MONTH)}))",
            C.ELIGIBLE_AR: f"={cell(C.PRE_CONCENTRATION)}-{cell(C.CONCENTRATION_EXCESS)}",
        }
        for metric, formula in formulas.items():
            ar_sheet[cell(metric)] = formula
    inv_sheet = schedule(book, "Inventory", INV_COLUMNS, inventory.to_dict("records"))
    for row in range(DATA_ROW, DATA_ROW + len(inventory)):
        cell = lambda metric: address(INV_COLUMNS, metric, row)
        for output, source in ((C.ELIGIBLE_COST, C.COST), (C.ELIGIBLE_NOLV, C.NOLV)):
            inv_sheet[cell(output)] = f"=IF({cell(C.ELIGIBLE)},{cell(source)},0)"
    records = certificates.merge(logs.loc[:, [C.MONTH, C.OPENING, C.DRAW, C.PAYDOWN]], on=C.MONTH).to_dict("records")
    cert_sheet = schedule(book, "Borrowing base", CERT_COLUMNS, records)
    inv_last = DATA_ROW + len(inventory) - 1
    for row, record in enumerate(records, start=DATA_ROW):
        cell = lambda metric, r=row: address(CERT_COLUMNS, metric, r)
        previous_outstanding = cell(C.OUTSTANDING, row - 1) if row > DATA_ROW else str(cfg.ABL_OPENING)
        inv_sum = lambda column: f"SUM('Inventory'!{address(INV_COLUMNS, column, DATA_ROW)}:{address(INV_COLUMNS, column, inv_last)})"
        formulas = {metric: f"=SUMIFS({ref(metric)},{ref(C.MONTH)},{cell(C.MONTH)})"
                    for metric in (C.GROSS_AR, C.ELIGIBLE_AR, C.CONCENTRATION_EXCESS)}
        formulas.update({
            C.ELIGIBLE_COST: f"={inv_sum(C.ELIGIBLE_COST)}",
            C.ELIGIBLE_NOLV: f"={inv_sum(C.ELIGIBLE_NOLV)}",
            C.AR_ADVANCE: f"={cell(C.ELIGIBLE_AR)}*{cfg.AR_ADVANCE}",
            C.INVENTORY_ADVANCE: f"=MIN({cell(C.ELIGIBLE_COST)}*{cfg.INVENTORY_COST_ADVANCE},{cell(C.ELIGIBLE_NOLV)}*{cfg.INVENTORY_NOLV_ADVANCE})",
            C.BASE: f"={cell(C.AR_ADVANCE)}+{cell(C.INVENTORY_ADVANCE)}",
            C.OPENING: f"={previous_outstanding}",
            C.DRAW: f"=MIN({cfg.ABL_DRAW},MAX(0,MIN({cell(C.BASE)},{cell(C.COMMITMENT)})-{cell(C.OPENING)}-{cell(C.RESERVES)}))",
            C.PAYDOWN: f"=MIN({cfg.ABL_PAYDOWN},{cell(C.OPENING)}+{cell(C.DRAW)})",
            C.OUTSTANDING: f"={cell(C.OPENING)}+{cell(C.DRAW)}-{cell(C.PAYDOWN)}",
            C.AVAILABILITY: f"=MIN({cell(C.BASE)},{cell(C.COMMITMENT)})-{cell(C.OUTSTANDING)}-{cell(C.RESERVES)}",
            C.SPRINGING: f"={cell(C.AVAILABILITY)}<{cfg.SPRINGING_THRESHOLD}*{cell(C.COMMITMENT)}",
            C.FCCR_TESTED: f'=IF({cell(C.SPRINGING)},{cell(C.FCCR)},"not tested")',
            C.FCCR_BREACH: f"=AND({cell(C.SPRINGING)},{cell(C.FCCR)}<{cfg.MIN_FCCR})",
        })
        for metric, formula in formulas.items():
            cert_sheet[cell(metric)] = formula


def build_workbook(properties: pd.DataFrame, draws: pd.DataFrame, balances: pd.DataFrame,
                   ar_details: pd.DataFrame, inventory: pd.DataFrame, certificates: pd.DataFrame,
                   logs: pd.DataFrame, facilities: pd.DataFrame, path=cfg.WORKBOOK) -> Path:
    book = Workbook()
    book.remove(book.active)
    book.properties.creator = book.properties.lastModifiedBy = cfg.AUTHOR
    book.calculation = CalcProperties(calcId=0, fullCalcOnLoad=True)
    cre_sheet(book, properties)
    covenants = schedule(book, "Covenants", COVENANT_COLUMNS, facilities.to_dict("records"))
    for row in range(DATA_ROW, DATA_ROW + len(facilities)):
        cell = lambda metric: address(COVENANT_COLUMNS, metric, row)
        formulas = {
            C.LEVERAGE: f'=IF({cell(C.EBITDA)}>0,{cell(C.DEBT)}/{cell(C.EBITDA)},"unavailable")',
            C.LEVERAGE_HEADROOM: f'=IF({cell(C.EBITDA)}>0,1-{cell(C.LEVERAGE)}/{cell(C.MAX_LEVERAGE)},"unavailable")',
            C.CUSHION: f'=IF({cell(C.EBITDA)}>0,1-{cell(C.DEBT)}/({cell(C.MAX_LEVERAGE)}*{cell(C.EBITDA)}),"unavailable")',
            C.FCCR_HEADROOM: f"=({cell(C.FCCR)}-{cell(C.MIN_FCCR)})/{cell(C.MIN_FCCR)}",
            C.LEVERAGE_BREACH: f"=OR({cell(C.EBITDA)}<=0,{cell(C.LEVERAGE)}>{cell(C.MAX_LEVERAGE)})",
            C.FCCR_BREACH: f"={cell(C.FCCR)}<{cell(C.MIN_FCCR)}",
        }
        for metric, formula in formulas.items():
            covenants[cell(metric)] = formula
    construction_sheets(book, draws, balances)
    abl_sheets(book, ar_details, inventory, certificates, logs)
    for sheet in book:
        sheet.freeze_panes = "B5"
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        if sheet.title == "CRE":
            sheet.page_setup.fitToHeight = 1
        sheet.print_title_rows = "1:4"
        sheet.print_options.horizontalCentered = True
        sheet.row_dimensions[HEADER_ROW].height = cfg.EXCEL_HEADER_HEIGHT
        for row in sheet:
            for cell in row:
                cell.font = Font(name=cfg.DOC_FONT, size=cfg.EXCEL_FONT_SIZE,
                                 bold=cell.row in (1, HEADER_ROW))
                cell.alignment = Alignment(vertical="top", wrap_text=cell.row == HEADER_ROW)
                if cell.row >= DATA_ROW and isinstance(cell.value, (float, int)) and not isinstance(cell.value, bool):
                    cell.number_format = cfg.NUMERIC_FORMAT
                header = sheet.cell(HEADER_ROW, cell.column).value
                if cell.row >= DATA_ROW and cell.data_type == "f" and header not in TEXT_OR_BOOLEAN_COLUMNS:
                    cell.number_format = cfg.NUMERIC_FORMAT
                if cell.row >= DATA_ROW and header in (C.LEVERAGE_HEADROOM, C.FCCR_HEADROOM, C.CUSHION,
                                                        C.RETAINAGE, C.COMPLETE):
                    cell.number_format = cfg.PERCENT_FORMAT
                if cell.row >= DATA_ROW and header == C.FLAGS:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
        if sheet.title != "CRE":
            sheet.auto_filter.ref = f"A{HEADER_ROW}:{get_column_letter(sheet.max_column)}{sheet.max_row}"
            for column in sheet.columns:
                first = column[0]
                sheet.column_dimensions[first.column_letter].width = min(
                    cfg.EXCEL_MAX_WIDTH, max(cfg.EXCEL_MIN_WIDTH, len(str(sheet.cell(HEADER_ROW, first.column).value)) + 2))
                if sheet.cell(HEADER_ROW, first.column).value == C.FLAGS:
                    sheet.column_dimensions[first.column_letter].width = cfg.EXCEL_MAX_WIDTH
            for row in sheet.iter_rows(min_row=DATA_ROW):
                line_count = 1
                for cell in row:
                    if isinstance(cell.value, str) and not cell.value.startswith("="):
                        cell.alignment = Alignment(vertical="top", wrap_text=True)
                        width = sheet.column_dimensions[cell.column_letter].width
                        line_count = max(line_count, math.ceil(len(cell.value) / max(1, width - 2)))
                if C.FLAGS in [sheet.cell(HEADER_ROW, cell.column).value for cell in row]:
                    line_count = max(line_count, 3)
                sheet.row_dimensions[row[0].row].height = max(cfg.EXCEL_MIN_HEIGHT, cfg.EXCEL_LINE_HEIGHT * line_count)
        else:
            for metric, row in CRE_ROWS.items():
                for column in (2, 3):
                    sheet.cell(row, column).number_format = cfg.PERCENT_FORMAT if metric in CRE_PERCENT_METRICS else cfg.NUMERIC_FORMAT
                    if metric == C.SUPERVISORY_FLAG:
                        sheet.cell(row, column).number_format = "General"
            for row in sheet.iter_rows(min_row=DATA_ROW, max_row=10, min_col=5, max_col=5):
                for cell in row:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
                    sheet.cell(cell.row, 6).number_format = cfg.PERCENT_FORMAT
            sheet["A41"].alignment = Alignment(wrap_text=True, vertical="top")
        sheet.print_area = f"A1:{get_column_letter(sheet.max_column)}{sheet.max_row}"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    book.save(path)
    return path


def find_libreoffice() -> str | None:
    for name in cfg.LIBREOFFICE_NAMES:
        executable = shutil.which(name)
        if executable:
            return executable
    return next((str(path) for path in cfg.LIBREOFFICE_PATHS if path.exists()), None)


def recalculate(path: Path, folder: Path) -> Path:
    executable = find_libreoffice()
    if not executable:
        raise FileNotFoundError("LibreOffice is not installed.")
    folder.mkdir(parents=True, exist_ok=True)
    profile = folder / "profile"
    command = [executable, f"-env:UserInstallation={profile.resolve().as_uri()}", "--headless",
               "--convert-to", "xlsx", "--outdir", str(folder.resolve()), str(path.resolve())]
    subprocess.run(command, check=True, capture_output=True, timeout=cfg.QA_RENDER_TIMEOUT)
    result = folder / path.name
    if not result.exists():
        raise RuntimeError("LibreOffice did not produce the recalculated workbook.")
    return result


if __name__ == "__main__":
    from credit_pack.run_all import main

    main()

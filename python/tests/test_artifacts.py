"""Generated output agreement, Word metadata, and actual Excel recalculation."""

import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell

from credit_pack import config as cfg, facility
from credit_pack.config import C
from excel.build_workbook import (AR_COLUMNS, BALANCE_COLUMNS, CERT_COLUMNS, COVENANT_COLUMNS,
                                  CRE_ROWS, DATA_ROW, DRAW_COLUMNS, INV_COLUMNS, address,
                                  find_libreoffice, recalculate)
from tests import inputs as fixture

# CONFIG: generated artifacts and OOXML namespaces inspected by these checks.
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
RECONCILIATION_PATH = cfg.OUTPUTS / "excel_reconciliation.csv"
ERROR_PREFIXES = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!")


def test_run_outputs_and_readme_agree(example_run):
    latest = pd.read_csv(cfg.OUTPUTS / "borrower_latest.csv")
    assert len(latest) == len(cfg.TICKERS)
    assert latest[C.SOURCE].eq(cfg.DEMO_SOURCE).all()
    assert example_run["portfolio_observations"] == cfg.PORTFOLIO_LOANS * cfg.PORTFOLIO_QUARTERS
    readme = (cfg.ROOT / "README.md").read_text(encoding="utf-8")
    for row in latest.to_dict("records"):
        assert f"{row[C.EBITDA]:,.4f}" in readme
    for record in json.loads((cfg.RAW / "demo" / "manifest.json").read_text(encoding="utf-8")):
        assert record["sha256"] in readme
        assert record["retrieved_at"] is None
    assert "No SEC snapshot was retrieved" in readme


def test_facility_break_even_and_amortization(example_run):
    financials = pd.read_csv(cfg.OUTPUTS / "borrower_latest.csv")
    for row in financials.to_dict("records"):
        proposal, schedule = facility.propose(row)
        assert schedule[C.PRINCIPAL].sum() == pytest.approx(proposal[C.TERM])
        assert schedule.tail(1)[C.OUTSTANDING].item() == pytest.approx(0, abs=cfg.EXCEL_TOLERANCE)
        threshold = row[C.EBITDA] * (1 - proposal[C.BREAK_EVEN])
        fccr = ((threshold - row[C.CAPEX] - row[C.TAX]) /
                (proposal[C.INTEREST] + proposal[C.PRINCIPAL]))
        assert fccr >= cfg.MIN_FCCR - cfg.TOLERANCE
        assert proposal[C.DEBT] / threshold <= cfg.MAX_LEVERAGE + cfg.TOLERANCE
        lower = threshold * (1 - cfg.TOLERANCE)
        test = facility.covenant_headroom(proposal[C.DEBT], lower,
                                          (lower - row[C.CAPEX] - row[C.TAX]) /
                                          (proposal[C.INTEREST] + proposal[C.PRINCIPAL]))
        assert test[C.BREACH]


def test_docx_author_headings_and_content(example_run):
    for ticker in cfg.TICKERS:
        path = cfg.OUTPUTS / f"memo_{ticker}.docx"
        with zipfile.ZipFile(path) as archive:
            core = archive.read("docProps/core.xml").decode()
            assert cfg.AUTHOR in core
            styles = ElementTree.fromstring(archive.read("word/styles.xml"))
            for style in styles.findall("w:style", WORD_NAMESPACE):
                name = style.get(f"{{{WORD_NAMESPACE['w']}}}styleId")
                if name in ("Heading1", "Heading2", "Heading3"):
                    assert style.find(".//w:color", WORD_NAMESPACE) is None
            content = archive.read("word/document.xml").decode()
            assert "Recommendation:" in content
            assert cfg.DEMO_SOURCE in content
            assert "Closing equity" in content
            assert "\u2014" not in content


def test_excel_plain_style_author_and_live_formulas(example_run):
    book = load_workbook(cfg.WORKBOOK)
    assert book.properties.creator == cfg.AUTHOR
    assert book["CRE"][f"B{CRE_ROWS[C.LOAN]}"].value.startswith("=MIN(")
    for sheet in book:
        assert sheet.sheet_properties.tabColor is None
        for row in sheet:
            for cell in row:
                assert cell.fill.patternType is None
                if not isinstance(cell, MergedCell):
                    assert cell.font.color is None
    book.close()


def test_excel_recalculates_and_reconciles_to_python(example_run, tmp_path):
    if not find_libreoffice():
        pytest.skip("LibreOffice not installed; native formula reconciliation skipped.")
    recalculated = recalculate(cfg.WORKBOOK, tmp_path / "recalculated")
    book = load_workbook(recalculated, data_only=True)
    checks = []

    def compare(sheet, cell, expected, label):
        actual = book[sheet][cell].value
        if isinstance(expected, (bool, np.bool_)):
            assert actual == bool(expected), (sheet, cell, actual, expected)
        elif isinstance(expected, str):
            assert actual == expected, (sheet, cell, actual, expected)
        else:
            assert actual == pytest.approx(expected, abs=cfg.EXCEL_TOLERANCE), (sheet, cell, actual, expected)
        checks.append({"sheet": sheet, "cell": cell, "metric": label, "python": expected,
                       "excel": actual, "result": "PASS"})

    cre_rows = pd.read_csv(cfg.OUTPUTS / "cre_sizing.csv")
    from openpyxl.utils import get_column_letter

    for column, record in enumerate(cre_rows.to_dict("records"), start=2):
        for metric in fixture.RUNTIME_COLUMNS:
            compare("CRE", f"{get_column_letter(column)}{CRE_ROWS[metric]}", record[metric], metric)
    comparisons = (
        ("Covenants", "facilities.csv", COVENANT_COLUMNS,
         (C.LEVERAGE, C.FCCR_HEADROOM, C.LEVERAGE_HEADROOM, C.CUSHION, C.LEVERAGE_BREACH, C.FCCR_BREACH)),
        ("Draws", "construction_draws.csv", DRAW_COLUMNS,
         (C.APPROVED, C.RETAINED, C.FUNDED, C.EQUITY_FUNDED, C.LOAN_FUNDED, C.CUM_APPROVED, C.CUM_EQUITY, C.CUM_LOAN)),
        ("Balance", "construction_balance.csv", BALANCE_COLUMNS,
         (C.COST_COMPLETE, C.UNDISBURSED, C.REMAINING_EQUITY, C.SHORTFALL, C.EQUITY_CALL,
          C.CONTINGENCY_LEFT, C.INTEREST_LEFT, C.INTEREST_REQUIRED)),
        ("AR eligibility", "abl_ar_detail.csv", AR_COLUMNS,
         (C.GROSS_AR, C.CROSS_AGED, C.PRE_CONCENTRATION, C.CONCENTRATION_EXCESS, C.ELIGIBLE_AR)),
        ("Borrowing base", "abl_certificates.csv", CERT_COLUMNS,
         (C.ELIGIBLE_AR, C.AR_ADVANCE, C.INVENTORY_ADVANCE, C.BASE, C.OUTSTANDING,
          C.AVAILABILITY, C.SPRINGING, C.FCCR_BREACH)),
    )
    for sheet, filename, columns, metrics in comparisons:
        for row, record in enumerate(pd.read_csv(cfg.OUTPUTS / filename).to_dict("records"), start=DATA_ROW):
            for metric in metrics:
                compare(sheet, address(columns, metric, row), record[metric], metric)
    for sheet in book:
        for row in sheet:
            for cell in row:
                assert cell.data_type != "e", (sheet.title, cell.coordinate, cell.value)
    book.close()
    pd.DataFrame(checks).to_csv(RECONCILIATION_PATH, index=False)


def test_excel_inputs_change_live_outputs(example_run, tmp_path):
    if not find_libreoffice():
        pytest.skip("LibreOffice not installed; input perturbation skipped.")
    changed = tmp_path / "changed.xlsx"
    book = load_workbook(cfg.WORKBOOK)
    cre_input = f"B{CRE_ROWS[C.RENT]}"
    original_rent = book["CRE"][cre_input].value
    book["CRE"][cre_input] = original_rent / 2
    book["Balance"][address(BALANCE_COLUMNS, C.COST_COMPLETE, DATA_ROW)] = fixture.BALANCE_FIXTURE[0]
    book["Balance"][address(BALANCE_COLUMNS, C.UNDISBURSED, DATA_ROW)] = fixture.BALANCE_FIXTURE[1]
    book["Balance"][address(BALANCE_COLUMNS, C.REMAINING_EQUITY, DATA_ROW)] = fixture.BALANCE_FIXTURE[2]
    book["Covenants"][address(COVENANT_COLUMNS, C.DEBT, DATA_ROW)] = fixture.COVENANT_DEBT
    book["Covenants"][address(COVENANT_COLUMNS, C.EBITDA, DATA_ROW)] = fixture.COVENANT_EBITDA
    book.save(changed)
    book.close()
    recalculated = recalculate(changed, tmp_path / "changed_recalculated")
    values = load_workbook(recalculated, data_only=True)
    original_cre = pd.read_csv(cfg.OUTPUTS / "cre_sizing.csv")
    assert values["CRE"][f"B{CRE_ROWS[C.LOAN]}"].value < original_cre.head(1)[C.LOAN].item()
    assert values["Balance"][address(BALANCE_COLUMNS, C.SHORTFALL, DATA_ROW)].value == fixture.BALANCE_SHORTFALL
    assert values["Balance"][address(BALANCE_COLUMNS, C.EQUITY_CALL, DATA_ROW)].value
    assert values["Covenants"][address(COVENANT_COLUMNS, C.CUSHION, DATA_ROW)].value == pytest.approx(fixture.COVENANT_CUSHION)
    values.close()

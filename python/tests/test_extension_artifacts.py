"""Offline integration, source hash checks, and native formula perturbations."""

import hashlib
import json
import socket

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook

from credit_pack import extension_config as cfg, issuer_research, run_extension
from credit_pack.extension_config import X
from excel.build_extension_workbook import (Builder, build, CERT_COLUMNS, DATA_ROW, PRICE_COLUMNS,
                                            SIZING_CELLS, address, verify_recalculated)
from excel.build_workbook import find_libreoffice, recalculate


@pytest.fixture(scope="module")
def extension_tables():
    return run_extension.collect_tables()


def test_extension_is_offline_and_public_values_are_selected_correctly(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Runtime network access is forbidden.")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    tables = run_extension.collect_tables()
    apple = tables["issuer_scorecards"].set_index(X.ISSUER).loc["Apple"]
    assert apple[X.DEBT] == 98_657_000_000
    assert apple[X.EBITDA] == 144_748_000_000
    assert apple[X.FCF_DEBT] == pytest.approx(98_767 / 98_657)
    assert set(tables["issuer_scorecards"][X.RECOMMENDATION]) == {"buy", "hold", "sell"}
    facts = tables["issuer_facts"]
    assert len(facts) == 15
    assert facts["url"].str.startswith("https://").all()
    assert facts["retrieved_at"].eq(cfg.SOURCE_DATE).all()


def test_public_fact_tamper_is_rejected(tmp_path):
    path = tmp_path / issuer_research.FACTS_FILE.name
    raw = issuer_research.FACTS_FILE.read_bytes()
    path.write_bytes(raw)
    record = {"path": path.name,
              "sha256": hashlib.sha256(raw).hexdigest()}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([record]), encoding="utf-8")
    assert len(issuer_research.load_facts(path, manifest)) == 15
    path.write_bytes(raw + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        issuer_research.load_facts(path, manifest)


def test_workbook_recalculates_all_controls_and_plain_style(extension_tables, tmp_path):
    path = tmp_path / "extension.xlsx"
    controls = build(extension_tables, path)
    book = load_workbook(path)
    assert book.properties.creator == cfg.base.AUTHOR
    for sheet in book:
        assert sheet.sheet_properties.tabColor is None
        for row in sheet:
            for cell in row:
                assert cell.fill.patternType is None
                assert cell.font.color is None
    book.close()
    if not find_libreoffice():
        pytest.skip("LibreOffice absent; native reconciliation not run.")
    result = verify_recalculated(recalculate(path, tmp_path / "calculated"), controls)
    assert result["result"].eq("PASS").all()


def test_live_input_changes_project_pool_tax_and_price(extension_tables, tmp_path):
    if not find_libreoffice():
        pytest.skip("LibreOffice absent; native perturbations not run.")
    path = tmp_path / "changed.xlsx"
    build(extension_tables, path)
    book = load_workbook(path)
    parameters = {}
    for row in book["Assumptions"].iter_rows(min_row=DATA_ROW):
        fields = {book["Assumptions"].cell(DATA_ROW - 1, cell.column).value: cell for cell in row}
        if fields[X.METRIC].value:
            parameters[fields[X.METRIC].value] = fields[X.VALUE].coordinate
    book["Assumptions"][parameters["project.target_dscr"]] = 3.0
    book["Assumptions"][parameters["warehouse.min_score"]] = 900
    book["Muni yields"]["C5"] = .4
    book["Price validation"][address(PRICE_COLUMNS, X.TRADE_PRICE, DATA_ROW)] = 200
    book.save(path)
    book.close()
    changed = load_workbook(recalculate(path, tmp_path / "calculated"), data_only=True)
    assert changed["Project cash"][SIZING_CELLS[X.LOAN]].value < 70e6
    assert changed["Warehouse dashboard"][address(CERT_COLUMNS, X.BASE, DATA_ROW)].value == 0
    assert changed["Warehouse dashboard"][address(CERT_COLUMNS, X.AVAILABILITY, DATA_ROW)].value < 0
    assert changed["Muni yields"]["E5"].value == pytest.approx(.032 / .6)
    assert changed["Price validation"][address(PRICE_COLUMNS, X.PRICE_BREAK, DATA_ROW)].value
    changed.close()

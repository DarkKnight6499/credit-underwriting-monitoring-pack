"""Fact-context rejection, fallback tags, debt flags, and snapshot integrity."""

import json

import pandas as pd
import pytest

from credit_pack import config as cfg, edgar, spreading
from credit_pack.config import C
from tests import inputs as fixture


def test_fallback_tag_recorded(companyfacts):
    spread, audit = spreading.spread(companyfacts, "FIXTURE", cfg.DEMO_SOURCE)
    latest = spread.loc[spread[C.YEAR] == fixture.FIXTURE_YEAR].to_dict("records")[0]
    assert latest[C.REVENUE] == fixture.FIXTURE_REVENUE
    lineage = audit.loc[(audit[C.YEAR] == fixture.FIXTURE_YEAR) & (audit[C.METRIC] == C.REVENUE)]
    assert lineage[C.TAG].item() == cfg.TAGS[C.REVENUE][-1]


@pytest.mark.parametrize("form", fixture.INVALID_FACT_FORMS)
def test_mismatched_form_dropped(companyfacts, form):
    tag = cfg.TAGS[C.REVENUE][-1]
    facts = companyfacts["facts"]["us-gaap"][tag]["units"][cfg.UNIT]
    facts.append({**facts[-1], "form": form, "val": fixture.INVALID_FACT_VALUE})
    value, _, _ = spreading.select_fact(companyfacts, C.REVENUE, fixture.FIXTURE_YEAR, fixture.FIXTURE_END)
    assert value == fixture.FIXTURE_REVENUE


@pytest.mark.parametrize("period", fixture.INVALID_FISCAL_PERIODS)
def test_fiscal_period_mismatch_dropped(companyfacts, period):
    tag = cfg.TAGS[C.REVENUE][-1]
    facts = companyfacts["facts"]["us-gaap"][tag]["units"][cfg.UNIT]
    facts.append({**facts[-1], "fp": period, "val": fixture.INVALID_FACT_VALUE})
    assert spreading.select_fact(companyfacts, C.REVENUE, fixture.FIXTURE_YEAR, fixture.FIXTURE_END)[0] == fixture.FIXTURE_REVENUE


@pytest.mark.parametrize("override", ({"end": fixture.INVALID_END}, {"filed": fixture.INVALID_FILED},
                                      {"start": fixture.FIXTURE_END}, {"fy": fixture.FIXTURE_YEAR - 1}))
def test_date_duration_or_year_mismatch_dropped(companyfacts, override):
    tag = cfg.TAGS[C.REVENUE][-1]
    facts = companyfacts["facts"]["us-gaap"][tag]["units"][cfg.UNIT]
    facts.append({**facts[-1], **override, "val": fixture.INVALID_FACT_VALUE})
    assert spreading.select_fact(companyfacts, C.REVENUE, fixture.FIXTURE_YEAR, fixture.FIXTURE_END)[0] == fixture.FIXTURE_REVENUE


def test_missing_debt_zero_and_flagged_other_missing_unavailable(companyfacts):
    spread, audit = spreading.spread(companyfacts, "FIXTURE", cfg.DEMO_SOURCE)
    assert (spread[C.DEBT_SHORT] == 0).all()
    assert spread[C.FLAGS].str.contains(f"zero_assumed:{C.DEBT_SHORT}").all()
    assert spread[C.CFO].isna().all()
    assert audit.loc[audit[C.METRIC] == C.DEBT_SHORT, C.TAG].eq("MISSING").all()


def test_too_few_years_is_explicit_error(companyfacts):
    tag = cfg.TAGS[C.REVENUE][-1]
    companyfacts["facts"]["us-gaap"][tag]["units"][cfg.UNIT].pop()
    with pytest.raises(ValueError, match="distinct annual"):
        spreading.fiscal_periods(companyfacts)


def test_cik_resolution_and_missing_ticker():
    directory = {str(index): {"ticker": ticker, "cik_str": cik}
                 for index, (ticker, cik) in enumerate(fixture.FIXTURE_CIKS.items())}
    assert edgar.resolve_ciks(directory) == fixture.FIXTURE_CIKS
    with pytest.raises(ValueError):
        edgar.resolve_ciks({})


def test_snapshot_manifest_hash_and_tamper_rejection(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "RAW", tmp_path)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"facts": {}}'

    def offline_opener(request, timeout):
        assert request.get_header("User-agent") == fixture.FIXTURE_UA
        assert timeout == cfg.REQUEST_TIMEOUT
        return Response()

    edgar.snapshot(fixture.FIXTURE_URL, cfg.TICKERS[0], fixture.FIXTURE_UA, offline_opener)
    payload, record = edgar.load_snapshot(cfg.TICKERS[0])
    assert payload == {"facts": {}}
    path = edgar.manifest_path().parent / record["path"]
    assert record["url"] == fixture.FIXTURE_URL
    assert record["retrieved_at"]
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        edgar.load_snapshot(cfg.TICKERS[0])


def test_missing_real_snapshot_does_not_substitute_demo(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "RAW", tmp_path)
    with pytest.raises(FileNotFoundError):
        edgar.load_snapshot(cfg.TICKERS[0])


def test_placeholder_user_agent_rejected():
    with pytest.raises(ValueError, match="actual contact email"):
        edgar.snapshot(fixture.FIXTURE_URL, cfg.TICKERS[0], cfg.SEC_USER_AGENT)


def test_real_snapshot_only_when_available():
    if not edgar.read_manifest():
        pytest.skip("No real SEC snapshot; offline fixtures cover selection logic.")
    facts, _ = edgar.load_snapshot(cfg.TICKERS[0])
    spread, _ = spreading.spread(facts, cfg.TICKERS[0], cfg.REAL_SOURCE)
    assert len(spread) == cfg.YEARS

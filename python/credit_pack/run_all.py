"""Run offline examples or explicitly supplied SEC snapshots and write reports."""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as cfg
from .config import C
from . import abl, construction, cre, edgar, facility, portfolio, rating, ratios, spreading
from .memo import markdown_table, write_credit_memo


def save(frame: pd.DataFrame, filename: str, processed=False) -> None:
    folder = cfg.PROCESSED if processed else cfg.OUTPUTS
    folder.mkdir(parents=True, exist_ok=True)
    frame.to_csv(folder / filename, index=False, float_format="%.10g")


def load_borrowers(mode: str) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    spreads, lineage, provenance = [], [], []
    demo_folder = cfg.RAW / "demo"
    if mode == cfg.MODE_DEMO:
        demo_folder.mkdir(parents=True, exist_ok=True)
    for index, ticker in enumerate(cfg.TICKERS):
        if mode == cfg.MODE_DEMO:
            facts = spreading.synthetic_companyfacts(ticker, cfg.SEED + index)
            raw = json.dumps(facts, indent=2).encode("utf-8")
            path = demo_folder / f"{ticker}.json"
            path.write_bytes(raw)
            record = {"name": ticker, "source": cfg.DEMO_SOURCE, "url": None,
                      "generated_at": cfg.AS_OF, "retrieved_at": None,
                      "sha256": hashlib.sha256(raw).hexdigest(), "path": str(path.relative_to(cfg.ROOT))}
            source = cfg.DEMO_SOURCE
        else:
            facts, record = edgar.load_snapshot(ticker)
            source = cfg.REAL_SOURCE
        spread, audit = spreading.spread(facts, ticker, source)
        spreads.append(spread)
        lineage.append(audit)
        provenance.append(record)
    if mode == cfg.MODE_DEMO:
        (demo_folder / "manifest.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return pd.concat(spreads, ignore_index=True), pd.concat(lineage, ignore_index=True), provenance


def charts(history: pd.DataFrame, migration: pd.DataFrame, quarterly: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=cfg.PLOT_SIZE)
    ax.plot(quarterly[C.QUARTER], quarterly[C.SHARE] * 100, marker="o", color="black")
    ax.set(ylabel="Watchlist balance (%)", title="Synthetic portfolio monitoring")
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    fig.savefig(cfg.OUTPUTS / "watchlist.png", dpi=cfg.PLOT_DPI, metadata={"Author": cfg.AUTHOR})
    plt.close(fig)
    matrix = migration.pivot(index=C.FROM_GRADE, columns=C.TO_GRADE, values=C.PROBABILITY)
    fig, ax = plt.subplots(figsize=cfg.PLOT_SIZE)
    plot = ax.imshow(matrix.to_numpy(), cmap="Greys", vmin=0, vmax=1)
    grades = list(matrix.index)
    ax.set_xticks(np.arange(len(grades)), grades)
    ax.set_yticks(np.arange(len(grades)), grades)
    ax.set(xlabel="Destination grade", ylabel="Origin grade", title="Synthetic quarterly rating migrations")
    fig.colorbar(plot, ax=ax, label="Transition probability")
    fig.tight_layout()
    fig.savefig(cfg.OUTPUTS / "migration.png", dpi=cfg.PLOT_DPI, metadata={"Author": cfg.AUTHOR})
    plt.close(fig)


def write_portfolio_report(history: pd.DataFrame, quarterly: pd.DataFrame,
                            industry: pd.DataFrame, property_mix: pd.DataFrame) -> None:
    paragraphs = ["# Quarterly portfolio report", "Synthetic loans and illustrative monitoring policy.",
                  markdown_table(quarterly)]
    for quarter in quarterly[C.QUARTER]:
        frame = history.loc[history[C.QUARTER] == quarter]
        watched = frame.loc[frame[C.WATCHLIST], [C.LOAN_ID, C.LOAN_TYPE, C.GRADE, C.CHANGE, C.BALANCE, C.TRIGGERS]]
        paragraphs.extend([f"## {quarter}", markdown_table(watched), "Industry concentrations",
                           markdown_table(industry.loc[industry[C.QUARTER] == quarter]),
                           "CRE property concentrations",
                           markdown_table(property_mix.loc[property_mix[C.QUARTER] == quarter])])
    (cfg.OUTPUTS / "portfolio_report.md").write_text("\n\n".join(paragraphs) + "\n", encoding="utf-8")


def write_readme(mode: str, provenance: list[dict]) -> None:
    latest = pd.read_csv(cfg.OUTPUTS / "borrower_latest.csv")
    sizes = pd.read_csv(cfg.OUTPUTS / "cre_sizing.csv")
    certificates = pd.read_csv(cfg.OUTPUTS / "abl_certificates.csv")
    quarterly = pd.read_csv(cfg.OUTPUTS / "portfolio_quarterly.csv")
    history = pd.read_csv(cfg.OUTPUTS / "portfolio_history.csv")
    final_quarter = quarterly.tail(1).to_dict("records")[0][C.QUARTER]
    watched = history.loc[(history[C.QUARTER] == final_quarter) & history[C.WATCHLIST],
                          [C.LOAN_ID, C.LOAN_TYPE, C.GRADE, C.BALANCE, C.TRIGGERS]]
    pd_table = pd.DataFrame([{C.GRADE: grade, C.PD: pd_value, C.CLASSIFICATION: cfg.CLASSIFICATION[grade]}
                             for grade, pd_value in cfg.PD_SCALE.items()])
    quant = pd.DataFrame([{C.FACTOR: factor, "higher_is_better": higher,
                           "ascending_boundaries": ", ".join(f"{value:g}" for value in boundaries),
                           C.WEIGHT: cfg.QUANT_WEIGHT * cfg.QUANT_WEIGHTS[factor]}
                          for factor, (higher, boundaries) in cfg.BANDS.items()])
    qualitative = pd.DataFrame([{C.TICKER: ticker, **inputs["qualitative"]}
                                for ticker, inputs in cfg.BORROWERS.items()])
    source_rows = pd.DataFrame([{"name": record["name"], "snapshot_date": record.get("retrieved_at") or "none (synthetic)",
                                "sha256": record["sha256"]} for record in provenance])
    mode_note = ("This run uses seeded synthetic companyfacts for labels HAS, WHR, and KSS. "
                 "These are scenario identifiers, not issuer financial statements or actual bank figures. "
                 "No SEC snapshot was retrieved."
                 if mode == cfg.MODE_DEMO else
                 "Corporate financials use hash-verified SEC snapshots. All proposed terms, qualitative judgments, "
                 "CRE, ABL, construction, and portfolio data remain illustrative.")
    build_note = ("Build environment: shell network connection to data.sec.gov failed. The web tool read the SEC ticker directory and API documentation but could not retrieve companyfacts for any requested borrower. The eCFR regulatory text worked. Consequently this demo has no SEC snapshot dates or hashes. The hashes below identify generated synthetic fixtures only; their manifest has null URL and retrieval time."
                  if mode == cfg.MODE_DEMO else
                  "Snapshots are real SEC companyfacts retrieved with the explicit fetcher; hashes and retrieval times come from the manifest. Operating income is not adjusted for non-cash impairments, so a goodwill charge lowers EBITDA and raises leverage. Tags absent from a filer's companyfacts are flagged in `data/processed/spread.csv` and `fact_lineage.csv`, and ratios that need them show unavailable.")
    text = f"""# Credit underwriting monitoring pack

Standalone corporate cash-flow, commercial real estate, construction, and asset-based lending model, with quarterly portfolio monitoring.

{mode_note}

## Run

Python 3.11 or later. Dependencies: numpy, pandas, matplotlib, openpyxl, python-docx, and pytest for tests. No network is required for the demo or tests. All inputs are in `python/credit_pack/config.py`. No GPU is used.

From the repository root in PowerShell, using an environment with the listed dependencies:

```powershell
$env:PYTHONPATH="$env:PYTHONPATH;python;."
python -m credit_pack.run_all
python -m pytest -q -p no:cacheprovider --basetemp=.pytest_tmp
```

If Python is not on PATH, use the full interpreter path and prepend its dependency directory to PYTHONPATH. `excel/build_workbook.py` also invokes the example runner. The workbook opens with automatic recalculation. Tests recalculate a disposable copy through LibreOffice when installed and skip that check otherwise.

For real corporate data, replace the illustrative contact placeholder in `SEC_USER_AGENT` with a descriptive organization and actual contact email. Run `python -m credit_pack.edgar` separately, then `python -m credit_pack.run_all --mode snapshots`. Snapshot mode fails when a file is absent or its hash is wrong. It never substitutes synthetic financials. Tests never call network endpoints.

## Corporate method

The spread uses the configured tag priority per metric and records tag, reporting start and end, filing date, accession, and source for every value in `data/processed/fact_lineage.csv`. It requires USD, form 10-K, fiscal period FY, a configured annual duration, an exact fiscal-end match, a matching fiscal label, and filing dates no later than the as-of date. Revenue contexts anchor the last five fiscal periods. Later comparative contexts with different FY metadata are excluded; restatements in those contexts are not incorporated. Missing debt components are zero with explicit flags; other missing facts remain unavailable. Required missing operating inputs prevent approval. Custom taxonomy extensions are not mapped. [SEC XBRL API documentation]({cfg.SEC_API_URL}), companyfacts section.

Formulas: EBITDA = operating income + D&A; total leverage = debt / EBITDA; net leverage = (debt - cash) / EBITDA; coverage = EBITDA / interest. FCCR = (EBITDA - capex - cash taxes) / (interest + scheduled principal). Historical scheduled principal is an illustrative zero input, not inferred from current debt. Debt / capitalization = debt / (debt + equity); current ratio = current assets / current liabilities; gross margin = (revenue - COGS) / revenue; EBITDA margin = EBITDA / revenue; FCF / debt = (CFO - capex) / debt. DSO, DIO, and DPO use average adjacent annual AR, inventory, and AP divided by revenue, COGS, and COGS respectively, multiplied by days per year. The first year has unavailable days because its opening balance is absent. Nonpositive ratio denominators remain unavailable.

The illustrative rating is ceil(0.70 x quantitative score + 0.30 x qualitative score). All factor scores run from one (best) to ten (worst). Each ascending boundary crosses one score band; equality gets the better score. Higher-is-better factors reverse the score direction. Margin stability is the sample standard deviation of the available five annual EBITDA margins. Missing quantitative inputs get the worst factor score. Nonpositive EBITDA imposes a grade floor above the conditional approval limit.

{markdown_table(quant)}

Illustrative qualitative inputs, on the same scale:

{markdown_table(qualitative)}

Illustrative qualitative weights within their block: industry risk {cfg.QUAL_WEIGHTS[C.INDUSTRY_RISK]:.0%}, management {cfg.QUAL_WEIGHTS[C.MANAGEMENT]:.0%}, market position {cfg.QUAL_WEIGHTS[C.POSITION]:.0%}, financial policy {cfg.QUAL_WEIGHTS[C.POLICY]:.0%}. Inputs represent scenario judgments, not issuer assessments. The following PD scale and mapping to classification labels are illustrative, not regulatory rating rules.

{markdown_table(pd_table, 4)}

Facility LGD uses the illustrative seniority and collateral table in `outputs/lgd_scale.csv`. The proposed package is replacement financing: revolver commitment = {cfg.REVOLVER_MULTIPLE:g} x EBITDA; term loan = {cfg.TERM_MULTIPLE:g} x EBITDA; revolver utilization {cfg.REVOLVER_UTILIZATION:.0%}; term amortization {cfg.TERM_YEARS} years; annual rate {cfg.FACILITY_RATE:.1%}. Closing equity must cover historical debt beyond proposed drawings. Covenants are illustrative max leverage {cfg.MAX_LEVERAGE:g}x and min FCCR {cfg.MIN_FCCR:g}x. Leverage headroom = 1 - actual leverage / maximum; FCCR headroom = actual FCCR / minimum - 1. EBITDA cushion = 1 - debt / (maximum leverage x EBITDA). Break-even EBITDA decline uses the tighter leverage or FCCR requirement, holding debt, interest, scheduled principal, capex, and taxes fixed. A negative value denotes an existing breach. The downside combines revenue {cfg.REVENUE_STRESS:.0%} and EBITDA margin {cfg.MARGIN_STRESS * 10000:.0f} basis points, with capex and taxes fixed.

Decision rule: decline for missing required inputs, grade above {cfg.CONDITIONAL_MAX_GRADE}, or a proposed base covenant breach. Otherwise approve with conditions if grade exceeds {cfg.APPROVE_MAX_GRADE}, downside breaches, or closing equity is needed. Otherwise approve. The rule is illustrative. Memos and facility schedules state the refinancing equity requirement.

## CRE and construction method

Potential gross income = quantity x in-place annual rent. Effective gross income = potential gross income x (1 - vacancy and credit loss) + other income. NOI = effective gross income - operating expenses - reserves. Market rent is disclosed for comparison and is not assumed achieved. Reserves are deducted in the model NOI convention. Value = NOI / cap rate. Debt constant = 12r / (1 - (1 + r)^(-n)), where r is annual rate / 12 and n is amortization years x 12. Sized loan = min(LTV limit x value, NOI / (minimum DSCR x debt constant), NOI / minimum debt yield). Stress uses rate +{cfg.CRE_RATE_STRESS * 10000:.0f} basis points and NOI {cfg.CRE_NOI_STRESS:.0%}, assuming a repricing loan.

Verified supervisory LTV limits: raw land 65%; land development 75%; commercial, multifamily and other nonresidential construction 80%; residential construction for one to four families 85%; improved property 85%. No supervisory limit is set for permanent owner-occupied one to four family and home equity loans. Absence of a limit does not mean unrestricted underwriting. Exceeding a limit is flagged as an exception, not an automatic prohibition. Source: [12 CFR part 208 Appendix C]({cfg.LTV_SOURCE}), Supervisory Loan-to-Value Limits table and footnote 2, plus Loans in Excess of the Supervisory Loan-to-Value Limits. Checked on {cfg.AS_OF}; eCFR displayed title 12 current through {cfg.LTV_SOURCE_CURRENT_THROUGH}.

Construction uses an illustrative line budget, equity-first cash funding, inspector completion caps, and {cfg.RETAINAGE:.0%} retainage on hard costs. Approved work less retainage is the cash draw, capped by available equity and commitment. Unpaid retainage remains in cost to complete. Funding covers land, hard costs, soft costs, contingency, and interest reserve. Monthly review flags completion excess, line overruns, contingency depletion, reserve shortfall, and funding shortages. Loan-in-balance requires undisbursed loan + remaining required equity >= forecast cost to complete; shortfall triggers an unfunded equity call. The scenario does not assume that the equity call is satisfied or release retainage automatically.

## ABL and portfolio method

The illustrative AR waterfall removes over-90-day invoices, cross-aged customers whose over-90 balance exceeds {cfg.CROSS_AGING_THRESHOLD:.0%}, affiliates, foreign AR, and contras. Concentration excess is each customer's eligible balance above {cfg.CONCENTRATION_LIMIT:.0%} of the eligible pool before concentration deductions. This fixed denominator is an explicit illustrative convention, avoiding circular calculation. Eligible AR advances at {cfg.AR_ADVANCE:.0%}. Inventory advances at min({cfg.INVENTORY_COST_ADVANCE:.0%} x eligible cost, {cfg.INVENTORY_NOLV_ADVANCE:.0%} x eligible NOLV), using aggregate eligible inventory. Availability = min(base, commitment) - outstanding - reserves. Negative availability is preserved. Springing FCCR is tested only when availability is strictly below {cfg.SPRINGING_THRESHOLD:.0%} of commitment. The monthly draw log caps drawings at available capacity before paydown. Customer exceptions remain traceable through the waterfall.

The synthetic portfolio has {cfg.PORTFOLIO_LOANS} loans across corporate, CRE (including construction), and ABL, observed for {cfg.PORTFOLIO_QUARTERS} quarters. Watchlist triggers: quarterly downgrade of at least {cfg.WATCH_DOWNGRADE} grades, covenant breach, CRE DSCR below {cfg.WATCH_DSCR:g}x, low ABL availability, construction out of balance, or supervisory LTV exception. Corporate covenants use synthetic debt, EBITDA, and debt service; CRE uses NOI and the monthly debt constant; ABL uses the same eligibility engine as the monthly certificates. Ratings are seeded synthetic states, not scorecard estimates for real loans. Migration counts use adjacent quarters only. Empty origin rows receive an explicitly conventional identity probability. Industry shares use the whole portfolio; property shares use CRE only.

## Generated results

The tables below are generated from the current CSV outputs, in USD and decimal fractions unless stated. Data mode: `{mode}`. Synthetic results are not bank figures.

### Borrower ratios and grades

{markdown_table(latest.loc[:, [C.TICKER, C.YEAR, C.REVENUE, C.EBITDA, C.LEVERAGE, C.FCCR, C.GRADE, C.PD, C.RECOMMENDATION]], 4)}

### CRE sizing

{markdown_table(sizes.loc[:, [C.PROPERTY, C.NOI, C.VALUE, C.LTV_LOAN, C.DSCR_LOAN, C.YIELD_LOAN, C.LOAN, C.BINDING, C.STRESS_DSCR]])}

### Latest ABL certificate

{markdown_table(certificates.tail(1).loc[:, [C.MONTH, C.ELIGIBLE_AR, C.AR_ADVANCE, C.INVENTORY_ADVANCE, C.BASE, C.OUTSTANDING, C.RESERVES, C.AVAILABILITY, C.SPRINGING, C.FCCR_BREACH]])}

### Quarterly portfolio

{markdown_table(quarterly)}

### Latest watchlist

{markdown_table(watched)}

## Data and provenance

SEC endpoint design: ticker directory resolves zero-padded CIKs and companyfacts supplies entity-wide USD XBRL facts. The explicit fetcher waits {cfg.REQUEST_INTERVAL:g} seconds between requests, below the SEC maximum, and writes immutable raw files with URL, retrieval timestamp, and SHA-256 in `data/raw/edgar/manifest.json`. [SEC fair access guidance]({cfg.SEC_ACCESS_URL}), Fair access section. A real contact email is required. Fetching is never part of tests or the demo.

{build_note}

{markdown_table(source_rows)}

`data/processed/` stores spreads, value lineage, and rating factor detail. `outputs/` stores all calculated CSVs, two PNG charts, Markdown and DOCX credit memos, a quarterly report, workbook reconciliation, and the run summary. `excel/credit_pack.xlsx` contains formula schedules for CRE, covenants, draws, construction balance, customer eligibility, inventory, and borrowing bases. The workbook is rebuilt from source on each run. Recalculation tests use a disposable copy and inspect formula errors and Python agreement.

## Limitations and illustrative assumptions

All credit policy bands, PDs, LGDs, qualitative inputs, rates, covenants, facilities, rent assumptions, collateral rules, forecasts, and synthetic portfolio states are illustrative. The supervisory LTV table is sourced regulatory guidance. Accounting tags require manual review before real use: companyfacts omits custom extensions, IFRS and non-USD data are excluded, debt may omit leases or other obligations, and fiscal metadata can exclude valid restated comparisons. No audited statement tie-out, lien search, collateral appraisal, legal review, environmental review, lease-level valuation, or actual credit approval is performed. Negative equity can make capitalization ratios economically misleading. Synthetic industries and summaries are scenario inputs. Construction completion is a simplified aggregate inspection; interest reserve need is an illustrative forecast and unpaid equity calls remain open. Credit decisions must not rely on this demonstration.
"""
    if cfg.EXTENSION_README.exists():
        text += cfg.EXTENSION_README.read_text(encoding="utf-8")
    (cfg.ROOT / "README.md").write_text(text, encoding="utf-8")


def main(mode=cfg.DEFAULT_MODE) -> dict:
    from excel.build_workbook import build_workbook

    for folder in (cfg.RAW, cfg.PROCESSED, cfg.OUTPUTS):
        folder.mkdir(parents=True, exist_ok=True)
    spread, lineage, provenance = load_borrowers(mode)
    financials = ratios.calculate(spread, cfg.HISTORICAL_PRINCIPAL)
    save(spread, "spread.csv", processed=True)
    save(lineage, "fact_lineage.csv", processed=True)
    save(financials, "borrower_ratios.csv")
    ratings, facilities, latest_rows, factors_all, schedules = [], [], [], [], []
    for ticker in cfg.TICKERS:
        history = financials.loc[financials[C.TICKER] == ticker]
        current = history.tail(1).to_dict("records")[0]
        score, factors = rating.scorecard(current, cfg.BORROWERS[ticker]["qualitative"])
        proposed, amortization = facility.propose(current)
        missing = [metric for metric in cfg.TAGS if metric not in cfg.DEBT_COMPONENTS and pd.isna(current[metric])]
        decision = facility.recommend(score, proposed, bool(missing))
        proposed.update({C.TICKER: ticker, C.RECOMMENDATION: decision})
        factors[C.TICKER] = ticker
        amortization[C.TICKER] = ticker
        ratings.append({C.TICKER: ticker, **score})
        facilities.append(proposed)
        latest_rows.append({**current, **score, C.RECOMMENDATION: decision})
        factors_all.append(factors)
        schedules.append(amortization)
        write_credit_memo(ticker, history, score, factors, proposed, decision)
    save(pd.DataFrame(ratings), "ratings.csv")
    save(pd.DataFrame(latest_rows), "borrower_latest.csv")
    save(pd.DataFrame(facilities), "facilities.csv")
    save(pd.concat(factors_all, ignore_index=True), "rating_factors.csv", processed=True)
    save(pd.concat(schedules, ignore_index=True), "amortization.csv")
    save(pd.DataFrame([{C.GRADE: grade, C.PD: value, C.CLASSIFICATION: cfg.CLASSIFICATION[grade]}
                       for grade, value in cfg.PD_SCALE.items()]), "pd_scale.csv")
    save(pd.DataFrame([{C.SENIORITY: key[0], C.COLLATERAL: key[1], C.LGD: value}
                       for key, value in cfg.LGD_TABLE.items()]), "lgd_scale.csv")
    rolls, sizes = cre.run_properties()
    draws, balances = construction.run_construction()
    certificates, logs, exceptions, details, inventory = abl.run_monthly()
    history = portfolio.synthetic_portfolio()
    _, migrations = portfolio.migration_matrix(history)
    quarterly = portfolio.quarterly_summary(history)
    industry = portfolio.concentration(history, C.INDUSTRY)
    property_mix = portfolio.concentration(history.loc[history[C.LOAN_TYPE] == "cre"], C.PROPERTY_TYPE)
    tables = {"cre_rent_roll.csv": rolls, "cre_sizing.csv": sizes,
              "construction_draws.csv": draws, "construction_balance.csv": balances,
              "abl_certificates.csv": certificates, "abl_draw_log.csv": logs,
              "abl_exceptions.csv": exceptions, "abl_ar_detail.csv": details,
              "abl_inventory.csv": inventory, "portfolio_history.csv": history,
              "migration_matrix.csv": migrations, "portfolio_quarterly.csv": quarterly,
              "industry_concentration.csv": industry, "property_concentration.csv": property_mix,
              "watchlist.csv": history.loc[history[C.WATCHLIST]]}
    for filename, frame in tables.items():
        save(frame, filename)
    build_workbook(rolls, draws, balances, details, inventory, certificates, logs, pd.DataFrame(facilities))
    charts(history, migrations, quarterly)
    write_portfolio_report(history, quarterly, industry, property_mix)
    write_readme(mode, provenance)
    summary = {"mode": mode, "seed": cfg.SEED, "as_of": cfg.AS_OF,
               "generated_at": datetime.now(timezone.utc).isoformat(),
               "borrower_grades": {row[C.TICKER]: row[C.GRADE] for row in ratings},
               "cre_sized_loans": dict(zip(sizes[C.PROPERTY], sizes[C.LOAN])),
               "abl_final_availability": float(certificates.tail(1)[C.AVAILABILITY].item()),
               "portfolio_loans": history[C.LOAN_ID].nunique(), "portfolio_observations": len(history),
               "latest_watchlist_count": int(quarterly.tail(1)[C.WATCH_COUNT].item()),
               "construction_final_shortfall": float(balances.tail(1)[C.SHORTFALL].item())}
    (cfg.OUTPUTS / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=(cfg.MODE_DEMO, cfg.MODE_SNAPSHOTS), default=cfg.DEFAULT_MODE)
    main(parser.parse_args().mode)

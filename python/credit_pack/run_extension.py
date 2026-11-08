"""Run all extension examples without network access."""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from . import extension_config as cfg, issuer_research, money_market, muni, price_validation, project_finance, warehouse
from .extension_config import X
from .memo import markdown_table

# CONFIG: deliverables and notes. Numeric model inputs are in extension_config.
SUMMARY_FILE = "extension_summary.json"
MEMO_PREFIX = "issuer_memo_"
TERM_SHEET = "mock_term_sheet.html"
WORK = cfg.base.ROOT / ".work"


def collect_tables():
    return {**project_finance.run_project(), **warehouse.run_warehouse(), **muni.run_muni(),
            **issuer_research.run_research(), **money_market.run_money_market(), **price_validation.run_prices()}


def write_memos(tables, output):
    for case in issuer_research.ISSUER_CASES:
        issuer = case[X.ISSUER]
        summary = tables["issuer_scorecards"].loc[tables["issuer_scorecards"][X.ISSUER].eq(issuer)].to_dict("records")[0]
        factors = tables["issuer_factors"].loc[tables["issuer_factors"][X.ISSUER].eq(issuer)]
        facts = tables["issuer_facts"].loc[tables["issuer_facts"][X.ISSUER].eq(issuer)]
        links = sorted({f"[{row['document']}]({row['url']})" for row in facts.to_dict("records")})
        note = {
            "corporate": "The debt measure includes current term debt, non-current term debt, and commercial paper. It excludes leases. EBITDA is operating income plus D&A under the existing pack convention. Historical cash flow supports the scenario, but the selected FY2025 statements are not a current surveillance update. Apple is the IG example; the rating reference and its scope are recorded in source_verification.md.",
            "gsib": "The selected CET1 measure is year-end Standardized CET1. LCR is the Firm average, not the bank subsidiary or a year-end spot measure. No capital requirement, GSIB surcharge, TLAC, resolution recovery, or regulatory headroom is calculated.",
            "go": "This is an issuer-level GO scenario. Financial inputs come from the County's release about its audited statements, not an EMMA disclosure. Revenue includes other financing sources; expense includes other uses. The fund balance ratio uses unassigned balance only. Bond-specific taxing authority, pledge, pension exposure, and legal remedies remain unverified.",
            "revenue": "The expense proxy excludes depreciation and includes O&M, administration, and other operating expenses. It is not a cash expense measure. Debt includes current and non-current bonds and notes. The report's coverage schedule nets carry-forwards and other adjustments, so this memo does not treat that figure as ordinary DSCR. Restricted cash is not assumed available. Bond-specific resolution coverage and EMMA disclosures remain unverified.",
        }[case[X.KIND]]
        text = f"""# {issuer}: mock issuer memo

As of {cfg.AS_OF}. Model call: **{summary[X.RECOMMENDATION].upper()}**. This is an illustrative call on a synthetic bond scenario, not an instruction to trade.

The equally weighted two-factor score is {summary[X.SCORE_AVG]:.2f} on a 1 (strongest) to 4 (weakest) scale. The offered spread is synthetic at {case[X.SPREAD] * 10000:.0f} bp. Buy requires score at most {cfg.SCORE_BUY_MAX:g} and spread at least {cfg.SCORE_MIN_SPREAD * 10000:.0f} bp. Hold applies through score {cfg.SCORE_HOLD_MAX:g}; a weaker score produces sell. Missing inputs require review. These bands are project policy, not agency ratings.

{markdown_table(factors.loc[:, [X.FACTOR, X.VALUE, X.FACTOR_SCORE, X.WEIGHT]], 4)}

{note}

Risk: {case['risk']} Catalyst: {case['catalyst']} Monitoring: {case['monitor']}

Sources: {', '.join(links)}. Field lineage, retrieval date, selected units, methodology references, and unresolved checks are in `issuer_facts.csv` and `docs/source_verification.md`. Calls mix public historical facts with synthetic spreads. No market price, instrument recommendation authority, or real-world validation is claimed.
"""
        filename = MEMO_PREFIX + issuer.lower().replace(" ", "_") + ".md"
        (output / filename).write_text(text, encoding="utf-8")


def write_term_sheet(tables, output):
    sized = tables["project_sizing"].to_dict("records")[0]
    construction = tables["project_construction"]
    project, facility = cfg.PROJECT, cfg.WAREHOUSE
    advance_terms = ", ".join(f"{grade} {rate:.0%}" for grade, rate in facility.advances)
    rows = [
        ("Status and parties", "Nonbinding synthetic illustration. Borrowers: Renewable Project SPV and Consumer Warehouse SPV. Lender: Example Credit Facility."),
        ("Project purpose and tenor", f"{cfg.PROJECT_CAPACITY_MW:g} MW illustrative solar asset, capacity factor {cfg.PROJECT_CAPACITY_FACTOR:.0%}. Construction: {len(construction)} months; operations and amortization: {cfg.PROJECT_YEARS} annual periods. No terminal balloon."),
        ("Project size and pricing", f"Debt ${sized[X.LOAN]:,.0f}; capex ${project.cost:,.0f}; fixed annual rate {project.rate:.2%}. Sizing: lower of PV of CFADS / {project.target_dscr:.2f}x and {project.max_cost_leverage:.0%} of capex."),
        ("Project funding", f"Equity first for capex. Equity pays construction interest ${construction[X.IDC].sum():,.0f} and initial DSRA ${sized[X.INITIAL_DSRA]:,.0f}. Interest uses opening debt plus half-period draws."),
        ("Project reserves and covenant", f"DSRA targets {project.dsra_years * 12:.0f} months of next annual service. Maintenance contribution ${cfg.PROJECT_MAINTENANCE:,.0f} annually; spend every {cfg.MAINTENANCE_CYCLE} years. DSCR covenant {project.covenant_dscr:.2f}x; distributions follow service and reserve top-up."),
        ("Warehouse commitment", f"${facility.commitment:,.0f} revolving commitment; {cfg.WAREHOUSE_MONTHS}-month illustration, then full repayment assumed due. Annual rate {facility.annual_rate:.2%}; no commitment fee in model."),
        ("Collateral and advance", f"Illustrative first-priority consumer receivables pledge. Verified income, no fraud/default, score at least {facility.min_score}, delinquency at most {facility.max_dpd} days, remaining term 1 to {facility.max_remaining} months. Advances: {advance_terms}."),
        ("Warehouse limits and reserves", f"State cap {facility.state_limit:.0%} and grade C cap {facility.grade_c_limit:.0%} of the fixed pre-concentration eligible pool. State haircut first; C haircut second. Pro rata allocation. Reserve ${facility.reserve:,.0f}."),
        ("Draw and cure mechanics", "Capacity is min(base, commitment) less reserve and debt. Principal collections sweep first; sponsor cash pays down next. Unfunded mandatory paydowns remain exceptions. Draws stop on covenant breach or uncured shortfall."),
        ("Warehouse covenants", f"Delinquency at most {facility.max_delinquency:.0%}; cumulative losses/original principal at most {facility.max_cumulative_default:.0%}; weighted pool APR at least {facility.min_apr:.0%}. Monthly certificate, cash reconciliation, and exception report."),
        ("Conditions and exclusions", "Illustrative diligence: title/lien, legal enforceability, servicing and backup servicing, collateral data, insurance, and reserve control review. No executed loan documents, legal opinion, counterparty commitment, or lender execution is demonstrated."),
    ]
    body = "\n".join(f"<tr><th>{label}</th><td>{text}</td></tr>" for label, text in rows)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="author" content="{cfg.base.AUTHOR}"><title>Mock facility term sheet</title><style>@page{{size:letter;margin:0.5in}}body{{font:10pt Arial;color:black}}h1{{font-size:16pt}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;vertical-align:top;padding:5px;border-bottom:1px solid black}}th{{width:24%}}tr{{break-inside:avoid}}</style></head><body><h1>Mock project and warehouse term sheet</h1><p>As of {cfg.AS_OF}. USD. All terms are illustrative.</p><table>{body}</table></body></html>"""
    (output / TERM_SHEET).write_text(html, encoding="utf-8")


def main(output=cfg.OUTPUT, workbook=cfg.WORKBOOK, recalc=False):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    tables = collect_tables()
    for name, frame in tables.items():
        frame.to_csv(output / f"{name}.csv", index=False, float_format="%.12g")
    write_memos(tables, output)
    write_term_sheet(tables, output)
    from excel.build_extension_workbook import build, recalculate_and_verify
    controls = build(tables, workbook)
    reconciliation = "not run; use --recalculate with LibreOffice installed"
    if recalc:
        checks = recalculate_and_verify(workbook, controls, WORK / "recalculated")
        checks.to_csv(output / "excel_reconciliation.csv", index=False)
        reconciliation = f"{len(checks)} comparisons passed in LibreOffice"
    summary = {"as_of": cfg.AS_OF, "seed": cfg.SEED, "project_debt": tables["project_sizing"][X.LOAN].item(),
               "warehouse_latest_availability": tables["warehouse_certificates"].tail(1)[X.AVAILABILITY].item(),
               "issuer_calls": tables["issuer_scorecards"].set_index(X.ISSUER)[X.RECOMMENDATION].to_dict(),
               "money_market_status": tables["money_market_summary"][X.STATUS].item(),
               "synthetic_price_breaks": int(tables["price_validation"][X.PRICE_BREAK].sum()),
               "workbook_reconciliation": reconciliation, "public_trade_data": "not obtained"}
    (output / SUMMARY_FILE).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    records = [{"path": str(path.relative_to(cfg.base.ROOT)).replace("\\", "/"),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "seed": cfg.SEED,
                "source": "Public selections only in issuer_facts; all other example inputs are synthetic or explicit policy"}
               for path in sorted(output.glob("*.csv"))]
    (output / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return tables, controls


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recalculate", action="store_true")
    main(recalc=parser.parse_args().recalculate)

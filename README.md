# Credit underwriting monitoring pack

Standalone corporate cash-flow, commercial real estate, construction, and asset-based lending model, with quarterly portfolio monitoring.

This run uses seeded synthetic companyfacts for labels HAS, WHR, and KSS. These are scenario identifiers, not issuer financial statements or actual bank figures. No SEC snapshot was retrieved.

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

The spread uses the configured tag priority per metric and records tag, reporting start and end, filing date, accession, and source for every value in `data/processed/fact_lineage.csv`. It requires USD, form 10-K, fiscal period FY, a configured annual duration, an exact fiscal-end match, a matching fiscal label, and filing dates no later than the as-of date. Revenue contexts anchor the last five fiscal periods. Later comparative contexts with different FY metadata are excluded; restatements in those contexts are not incorporated. Missing debt components are zero with explicit flags; other missing facts remain unavailable. Required missing operating inputs prevent approval. Custom taxonomy extensions are not mapped. [SEC XBRL API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), companyfacts section.

Formulas: EBITDA = operating income + D&A; total leverage = debt / EBITDA; net leverage = (debt - cash) / EBITDA; coverage = EBITDA / interest. FCCR = (EBITDA - capex - cash taxes) / (interest + scheduled principal). Historical scheduled principal is an illustrative zero input, not inferred from current debt. Debt / capitalization = debt / (debt + equity); current ratio = current assets / current liabilities; gross margin = (revenue - COGS) / revenue; EBITDA margin = EBITDA / revenue; FCF / debt = (CFO - capex) / debt. DSO, DIO, and DPO use average adjacent annual AR, inventory, and AP divided by revenue, COGS, and COGS respectively, multiplied by days per year. The first year has unavailable days because its opening balance is absent. Nonpositive ratio denominators remain unavailable.

The illustrative rating is ceil(0.70 x quantitative score + 0.30 x qualitative score). All factor scores run from one (best) to ten (worst). Each ascending boundary crosses one score band; equality gets the better score. Higher-is-better factors reverse the score direction. Margin stability is the sample standard deviation of the available five annual EBITDA margins. Missing quantitative inputs get the worst factor score. Nonpositive EBITDA imposes a grade floor above the conditional approval limit.

| factor | higher_is_better | ascending_boundaries | weight |
| :-- | :-- | :-- | :-- |
| total_leverage | No | 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4.5, 6 | 0.210 |
| interest_coverage | Yes | 1, 1.25, 1.5, 2, 3, 4, 6, 8, 12 | 0.175 |
| revenue | Yes | 5e+07, 1e+08, 2.5e+08, 5e+08, 1e+09, 2e+09, 5e+09, 1e+10, 2e+10 | 0.105 |
| margin_stability | No | 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.08 | 0.105 |
| current_ratio | Yes | 0.6, 0.8, 1, 1.1, 1.25, 1.5, 1.75, 2, 2.5 | 0.105 |

Illustrative qualitative inputs, on the same scale:

| ticker | industry_risk | management | market_position | financial_policy |
| :-- | :-- | :-- | :-- | :-- |
| HAS | 4.00 | 3.00 | 3.00 | 4.00 |
| WHR | 6.00 | 5.00 | 4.00 | 6.00 |
| KSS | 8.00 | 6.00 | 7.00 | 7.00 |

Illustrative qualitative weights within their block: industry risk 30%, management 25%, market position 25%, financial policy 20%. Inputs represent scenario judgments, not issuer assessments. The following PD scale and mapping to classification labels are illustrative, not regulatory rating rules.

| grade | pd | classification |
| :-- | :-- | :-- |
| 1 | 0.0002 | Pass |
| 2 | 0.0005 | Pass |
| 3 | 0.0010 | Pass |
| 4 | 0.0025 | Pass |
| 5 | 0.0050 | Pass |
| 6 | 0.0100 | Pass |
| 7 | 0.0250 | Special Mention |
| 8 | 0.0800 | Substandard |
| 9 | 0.2500 | Doubtful |
| 10 | 1.0000 | Loss |

Facility LGD uses the illustrative seniority and collateral table in `outputs/lgd_scale.csv`. The proposed package is replacement financing: revolver commitment = 0.75 x EBITDA; term loan = 1.5 x EBITDA; revolver utilization 50%; term amortization 5 years; annual rate 7.5%. Closing equity must cover historical debt beyond proposed drawings. Covenants are illustrative max leverage 3.5x and min FCCR 1.25x. Leverage headroom = 1 - actual leverage / maximum; FCCR headroom = actual FCCR / minimum - 1. EBITDA cushion = 1 - debt / (maximum leverage x EBITDA). Break-even EBITDA decline uses the tighter leverage or FCCR requirement, holding debt, interest, scheduled principal, capex, and taxes fixed. A negative value denotes an existing breach. The downside combines revenue -15% and EBITDA margin -300 basis points, with capex and taxes fixed.

Decision rule: decline for missing required inputs, grade above 7, or a proposed base covenant breach. Otherwise approve with conditions if grade exceeds 5, downside breaches, or closing equity is needed. Otherwise approve. The rule is illustrative. Memos and facility schedules state the refinancing equity requirement.

## CRE and construction method

Potential gross income = quantity x in-place annual rent. Effective gross income = potential gross income x (1 - vacancy and credit loss) + other income. NOI = effective gross income - operating expenses - reserves. Market rent is disclosed for comparison and is not assumed achieved. Reserves are deducted in the model NOI convention. Value = NOI / cap rate. Debt constant = 12r / (1 - (1 + r)^(-n)), where r is annual rate / 12 and n is amortization years x 12. Sized loan = min(LTV limit x value, NOI / (minimum DSCR x debt constant), NOI / minimum debt yield). Stress uses rate +200 basis points and NOI -10%, assuming a repricing loan.

Verified supervisory LTV limits: raw land 65%; land development 75%; commercial, multifamily and other nonresidential construction 80%; residential construction for one to four families 85%; improved property 85%. No supervisory limit is set for permanent owner-occupied one to four family and home equity loans. Absence of a limit does not mean unrestricted underwriting. Exceeding a limit is flagged as an exception, not an automatic prohibition. Source: [12 CFR part 208 Appendix C](https://www.ecfr.gov/current/title-12/chapter-II/subchapter-A/part-208/appendix-Appendix%20C%20to%20Part%20208), Supervisory Loan-to-Value Limits table and footnote 2, plus Loans in Excess of the Supervisory Loan-to-Value Limits. Checked on 2026-10-21; eCFR displayed title 12 current through 2026-10-19.

Construction uses an illustrative line budget, equity-first cash funding, inspector completion caps, and 10% retainage on hard costs. Approved work less retainage is the cash draw, capped by available equity and commitment. Unpaid retainage remains in cost to complete. Funding covers land, hard costs, soft costs, contingency, and interest reserve. Monthly review flags completion excess, line overruns, contingency depletion, reserve shortfall, and funding shortages. Loan-in-balance requires undisbursed loan + remaining required equity >= forecast cost to complete; shortfall triggers an unfunded equity call. The scenario does not assume that the equity call is satisfied or release retainage automatically.

## ABL and portfolio method

The illustrative AR waterfall removes over-90-day invoices, cross-aged customers whose over-90 balance exceeds 50%, affiliates, foreign AR, and contras. Concentration excess is each customer's eligible balance above 20% of the eligible pool before concentration deductions. This fixed denominator is an explicit illustrative convention, avoiding circular calculation. Eligible AR advances at 85%. Inventory advances at min(50% x eligible cost, 85% x eligible NOLV), using aggregate eligible inventory. Availability = min(base, commitment) - outstanding - reserves. Negative availability is preserved. Springing FCCR is tested only when availability is strictly below 10% of commitment. The monthly draw log caps drawings at available capacity before paydown. Customer exceptions remain traceable through the waterfall.

The synthetic portfolio has 40 loans across corporate, CRE (including construction), and ABL, observed for 8 quarters. Watchlist triggers: quarterly downgrade of at least 2 grades, covenant breach, CRE DSCR below 1x, low ABL availability, construction out of balance, or supervisory LTV exception. Corporate covenants use synthetic debt, EBITDA, and debt service; CRE uses NOI and the monthly debt constant; ABL uses the same eligibility engine as the monthly certificates. Ratings are seeded synthetic states, not scorecard estimates for real loans. Migration counts use adjacent quarters only. Empty origin rows receive an explicitly conventional identity probability. Industry shares use the whole portfolio; property shares use CRE only.

## Generated results

The tables below are generated from the current CSV outputs, in USD and decimal fractions unless stated. Data mode: `demo`. Synthetic results are not bank figures.

### Borrower ratios and grades

| ticker | fiscal_year | revenue | ebitda | total_leverage | fccr | grade | pd | recommendation |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| HAS | 2025 | 4,967,158,008.0000 | 902,159,706.8000 | 2.1600 | 5.1071 | 4 | 0.0025 | approve with conditions |
| WHR | 2025 | 15,680,258,720.0000 | 1,624,876,017.0000 | 3.5640 | 2.7607 | 5 | 0.0050 | approve with conditions |
| KSS | 2025 | 12,740,198,400.0000 | 890,500,681.1000 | 5.4000 | 1.5740 | 7 | 0.0250 | approve with conditions |

### CRE sizing

| property | noi | value | ltv_loan | dscr_loan | debt_yield_loan | sized_loan | binding_constraint | stressed_dscr |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| Maple Apartments | 1,260,400.00 | 21,006,666.67 | 15,755,000.00 | 14,014,943.39 | 14,004,444.44 | 14,004,444.44 | debt_yield_loan | 0.92 |
| Cedar Office | 1,019,200.00 | 13,589,333.33 | 10,192,000.00 | 11,332,934.23 | 11,324,444.44 | 10,192,000.00 | ltv_loan | 1.02 |

### Latest ABL certificate

| month | eligible_ar | ar_advance | inventory_advance | borrowing_base | outstanding | reserves | excess_availability | springing_fccr_test | fccr_breach |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 12 | 1,568,934.56 | 1,333,594.38 | 675,000.00 | 2,008,594.38 | 1,330,000.00 | 75,000.00 | 595,000.00 | No | No |

### Quarterly portfolio

| quarter | loan_count | balance | watchlist_count | watchlist_balance | balance_share |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 2024Q1 | 40 | 228,884,442.90 | 11 | 64,608,620.49 | 0.28 |
| 2024Q2 | 40 | 229,610,622.40 | 14 | 73,179,116.00 | 0.32 |
| 2024Q3 | 40 | 223,714,973.20 | 9 | 55,884,523.89 | 0.25 |
| 2024Q4 | 40 | 220,987,273.20 | 13 | 79,900,099.35 | 0.36 |
| 2025Q1 | 40 | 217,316,349.10 | 11 | 61,281,779.28 | 0.28 |
| 2025Q2 | 40 | 216,465,861.60 | 9 | 54,262,747.92 | 0.25 |
| 2025Q3 | 40 | 213,073,320.80 | 10 | 61,105,671.36 | 0.29 |
| 2025Q4 | 40 | 208,844,525.10 | 15 | 86,274,858.50 | 0.41 |

### Latest watchlist

| loan_id | loan_type | grade | balance | watchlist_triggers |
| :-- | :-- | :-- | :-- | :-- |
| L008 | cre | 10 | 7,614,929.79 | construction_out_of_balance |
| L010 | corporate | 5 | 1,799,563.56 | covenant_breach |
| L011 | cre | 6 | 10,300,797.17 | covenant_breach |
| L013 | corporate | 3 | 2,386,542.45 | covenant_breach |
| L016 | corporate | 4 | 2,592,080.85 | covenant_breach |
| L017 | cre | 4 | 9,590,157.68 | construction_out_of_balance |
| L019 | corporate | 6 | 9,948,276.44 | downgrade_2_or_more |
| L020 | cre | 5 | 6,897,922.09 | covenant_breach |
| L024 | abl | 9 | 1,896,526.23 | covenant_breach;abl_low_availability |
| L026 | cre | 4 | 8,072,529.49 | covenant_breach |
| L027 | abl | 5 | 1,882,857.62 | covenant_breach;abl_low_availability |
| L031 | corporate | 5 | 1,260,023.45 | covenant_breach |
| L035 | cre | 8 | 7,415,337.41 | construction_out_of_balance |
| L037 | corporate | 2 | 4,064,056.52 | covenant_breach |
| L038 | cre | 7 | 10,553,257.74 | covenant_breach |

## Data and provenance

SEC endpoint design: ticker directory resolves zero-padded CIKs and companyfacts supplies entity-wide USD XBRL facts. The explicit fetcher waits 0.2 seconds between requests, below the SEC maximum, and writes immutable raw files with URL, retrieval timestamp, and SHA-256 in `data/raw/edgar/manifest.json`. [SEC fair access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), Fair access section. A real contact email is required. Fetching is never part of tests or the demo.

Build environment: shell network connection to data.sec.gov failed. The web tool read the SEC ticker directory and API documentation but could not retrieve companyfacts for any requested borrower. The eCFR regulatory text worked. Consequently this demo has no SEC snapshot dates or hashes. The hashes below identify generated synthetic fixtures only; their manifest has null URL and retrieval time.

| name | snapshot_date | sha256 |
| :-- | :-- | :-- |
| HAS | none (synthetic) | 60458f3117697e6f4eb8c6ba95656d04c70cf209e36de9cd61cddfedc39bee22 |
| WHR | none (synthetic) | 1ea83638ec6ff91ae70674efccaad8d7dc4d9fa21c9bee9c8e47053394879258 |
| KSS | none (synthetic) | 31f9635c433bf7596fbe9ea2c64a6da07ab7505154c507015f32c50dd54603cc |

`data/processed/` stores spreads, value lineage, and rating factor detail. `outputs/` stores all calculated CSVs, two PNG charts, Markdown and DOCX credit memos, a quarterly report, workbook reconciliation, and the run summary. `excel/credit_pack.xlsx` contains formula schedules for CRE, covenants, draws, construction balance, customer eligibility, inventory, and borrowing bases. The workbook is rebuilt from source on each run. Recalculation tests use a disposable copy and inspect formula errors and Python agreement.

## Limitations and illustrative assumptions

All credit policy bands, PDs, LGDs, qualitative inputs, rates, covenants, facilities, rent assumptions, collateral rules, forecasts, and synthetic portfolio states are illustrative. The supervisory LTV table is sourced regulatory guidance. Accounting tags require manual review before real use: companyfacts omits custom extensions, IFRS and non-USD data are excluded, debt may omit leases or other obligations, and fiscal metadata can exclude valid restated comparisons. No audited statement tie-out, lien search, collateral appraisal, legal review, environmental review, lease-level valuation, or actual credit approval is performed. Negative equity can make capitalization ratios economically misleading. Synthetic industries and summaries are scenario inputs. Construction completion is a simplified aggregate inspection; interest reserve need is an illustrative forecast and unpaid equity calls remain open. Credit decisions must not rely on this demonstration.

## Project finance, warehouse, and fixed income extension

The extension adds a synthetic solar project with construction funding, DSCR sculpting, DSRA and maintenance reserves, and a fixed-debt sensitivity grid. A seeded consumer warehouse includes loan eligibility, concentration deductions, grade advance rates, certificates, cash-limited paydowns, draw blocking, and monthly covenants.

Four issuer memos combine named public historical facts with synthetic spreads and illustrative buy/hold/sell policy. GO and revenue muni scenarios include distinct credit metrics, tax-equivalent yields, and relative value. A Rule 2a-7 subset uses verified current eCFR parameters. Curve-based price checks demonstrate synthetic TRACE/EMMA-shaped inputs; no actual TRACE/EMMA trade or EMMA disclosure was obtained.

```powershell
$env:PYTHONPATH="python;."
python -m credit_pack.run_extension --recalculate
```

Use the configured interpreter path in [extension instructions](docs/extension.md) if `python` is not on PATH. Results and mock memos are in `examples/output/`; the [live-formula workbook](excel/credit_extension.xlsx) is separate from the original workbook. [Mock term sheet](examples/output/mock_term_sheet.html) is formatted for one printed letter page. The source ledger records [verified text and failed routes](docs/source_verification.md). All added model inputs are in `python/credit_pack/extension_config.py` or clearly marked module config blocks. No runtime network access is needed.

Limitations: simplified renewable generation and reserve waterfalls; stylized consumer losses; two-factor issuer scores; historical manual public selections; unverified bond-specific muni pledges and tax status; incomplete Rule 2a-7 coverage; synthetic market prices. Native formula reconciliation and hand-computed tests establish mechanical agreement, not real-world validation.

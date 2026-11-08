# Source verification

Retrieval date for this extension: **2026-11-08**. Primary URLs were opened with the web tool. Selected numeric facts are stored in `data/extension/public_issuer_facts.json`, with document, section, units, date, and field-level qualification. Its manifest hash covers the selection, not the original documents. No synthetic observation is attributed to EDGAR, TRACE, or EMMA.

## Rule text

[17 CFR 270.2a-7](https://www.ecfr.gov/current/title-17/chapter-II/part-270/section-270.2a-7), Money market funds. eCFR displayed title 17 current through 2026-11-05. Verified parameter subset:

| Section | Verified requirement used |
| :-- | :-- |
| (a)(11)(i), (d)(1)(i) | 397 calendar days; minimal credit risk analysis for private eligible securities |
| (d)(1)(ii), (iii) | Market-value-weighted WAM 60 days; WAL 120 days |
| (d)(2)(i) | USD-denominated eligible securities |
| (d)(3)(i)(A)(1), (ii)(F) | General 5% issuer limit; affiliated issuer aggregation |
| (d)(4)(i) | Illiquid acquisitions restricted above 5% |
| (d)(4)(ii) | Non-daily acquisitions restricted below 25% daily liquidity; tax-exempt funds excluded |
| (d)(4)(iii) | Non-weekly acquisitions restricted below 50% weekly liquidity |
| (a)(8), (a)(28) | Daily and weekly liquid-asset definitions |

The implementation supports plain fixed-rate instruments and direct US obligations. Liquidity classifications and consolidated issuer groups are reviewed inputs. It omits the temporary 25% issuer exception, single-state rules, guarantees, demand features, ABS look-through, maturity exceptions, fees, stress testing, and governance. A subset pass is not a compliance determination. The [SEC 2023 adopting release, 33-11211](https://www.sec.gov/files/rules/final/2023/33-11211.pdf), section II.C, corroborates the liquidity amendment; current parameters come from eCFR.

[12 CFR part 208 Appendix C](https://www.ecfr.gov/current/title-12/chapter-II/subchapter-A/part-208/appendix-Appendix%20C%20to%20Part%20208), Supervisory Loan-to-Value Limits table, footnote 2, and Loans in Excess section: rechecked the existing pack's 65/75/80/85/85% limits and owner-occupied exception. These are supervisory guidelines, not absolute lending prohibitions. No new accounting-standard assertion is introduced; EBITDA and other proxies are project definitions.

## Public financial selections

| Source | Document and section | Verification and limits |
| :-- | :-- | :-- |
| [Apple EDGAR filing](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm) | FY2025 10-K; statements pp.29, 31, 33; Note 9 | Opened. Operating income 133,050; D&A 11,698; CFO 111,482; capex 12,715; current term debt 12,350; non-current term debt 78,328; commercial paper 7,979. Original USD millions, converted to USD. Leases excluded from the debt proxy. |
| [JPMorgan Chase EDGAR filing](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm) | FY2025 10-K; Selected Financial Data, Capital Risk Management, Liquidity Risk Management | Opened. Year-end Standardized CET1 14.6%; Firm average LCR 111%. The subsidiary average LCR is different and is not substituted. GSIB context appears in Supervision and Regulation and Capital Risk Management; no surcharge is modelled. |
| [Dutchess County Comptroller](https://www.dutchessny.gov/Departments/Comptroller/Independent-Audit-of-Basic-Financial-Statements-for-2025.htm) | 2026-10-02 release about 2025 audited statements; paragraphs beginning “The audit affirmed” and “The audited financial statements” | Opened. General Fund revenues and other sources 590,825,562; expenditures and other uses 602,682,425; unassigned balance 81,593,243 USD. This is the issuer's release, not the underlying audited report or an EMMA filing. |
| [NYC Water and Sewer System](https://www.nyc.gov/assets/nycwaterboard/downloads/pdf/statements_and_reports/wb-financial-statements-2025.pdf) | FY2025 ACFR; combining statements pp.37, 40; coverage table p.82 | Web-extracted PDF text read. Operating revenue 4,821,078; O&M 2,161,383; administration 45,636; other operating expense 150,445; debt 36,158,597, all USD thousands. The model sums expenses excluding D&A. This is an accrual expense proxy. Coverage in p.82 includes netting and carry-forward effects, so it is not used as ordinary DSCR. |

FY2025 is a deliberate historical selection, not a claim that these are the latest available statements. [S&P's 2026-11-05 Apple note rating announcement](https://spratings.spglobal.com/ratings/%5Blang%5D/regulatory/article/-/view/type/HTML/id/3655103) was visible in the primary publisher's indexed text: AA+ on the announced senior notes, matching its long-term issuer rating. The opened page returned an empty body. This is partial verification of IG context, not a validated rating on any example security. Example securities have synthetic IDs.

## Methodology context

| Publisher text | Section read | Status and use |
| :-- | :-- | :-- |
| [Fitch Corporate Rating Criteria, 2026-01-09](https://assets.fitchratings.com/downloadFile?reportType=report&sfReport=false&slug=corporate-finance/corporate-rating-criteria-09-01-2026) | Scope, Key Rating Drivers, Appendix 9 | Verified. Business profile, financial profile, governance, and operating environment provide context. |
| [Fitch Bank Rating Criteria, 2026-05-08, alternate publisher asset](https://assets.fitchratings.com/downloadFile?reportType=report&sfReport=false&slug=ja%2Fbanks%2Fbank-rating-criteria-11-05-2026) | Viability Rating overview; Capitalisation and Leverage; Funding and Liquidity | Verified English text from alternate publisher endpoint. The ordinary English PDF endpoint failed. The model uses CET1 and LCR as illustrative indicators and does not reproduce the agency model. |
| [Fitch Local Government Model Summary, 2025-07-01](https://assets.ctfassets.net/03fbs7oah13w/2uFRhR87n2NMww70KLFwC5/93ae5a661caf19a45ba117956a17783e/MSD_20250701_3880-P.pdf) | Sections 3 and 5 | Verified publisher model summary. Financial resilience, demographics, and liability burden inform the review checklist. The current 2026 full criteria landing page opened, but its PDF did not. Current detailed calibration remains unverified and is not used. |
| [Fitch US Water and Sewer Rating Criteria, 2026-02-17](https://assets.fitchratings.com/downloadFile?reportType=report&sfReport=false&slug=us-public-finance/us-water-sewer-rating-criteria-17-02-2026) | Scope and Key Rating Drivers | Verified. Revenue defensibility, operating risk, financial profile, and asymmetric risks inform memo topics. |

All score bands, equal weights, monitoring thresholds, and buy/hold/sell policies are original illustrative assumptions. They are not rating-agency calibrations or published ratings.

## Market access, failed routes, and reproducibility

- [FINRA TRACE](https://www.finra.org/filing-reporting/trace), Overview and Technical Documentation: opened. [Fixed Income Data](https://www.finra.org/finra-data/fixed-income), Security Lookup: opened; search requires the user agreement and interactive lookup. No transaction rows were obtained. The alternate browse-catalog URL failed. Synthetic trade prices are model prices plus configured offsets; tolerance checks are mechanical demonstrations, not empirical validation.
- [EMMA root](https://emma.msrb.org/) and [Overview](https://emma.msrb.org/AboutEmma/Overview): both returned HTTP 403. No EMMA disclosure, trade, CUSIP, or transaction date is claimed verified. [MSRB Municipal Bond Basics](https://www.msrb.org/Education/Municipal-Bond-Basics-0), Bond Types and Tax Status, opened and supports the generic GO/revenue distinction. Specific pledges and tax exemptions remain unverified inputs.
- Shell `curl.exe -L -A "Mozilla/5.0"` attempted direct NYC PDF, Fitch bank PDF, and EMMA URLs. All failed to connect in the offline shell. `python -m markitdown` failed because the module is absent. No package installation was attempted. Web PDF text was used instead; the water-table screenshot also failed with cache miss. Original source documents were not downloaded into the repository.
- SEC API and fair-access pages opened: [XBRL Data APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) and [Fair access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data). Existing snapshot hashes are retained. Optional `python/tools/fetch_extension_sources.py` writes separate raw files and a success/failure manifest. It is not imported by the library, demo, or tests and was not run in this offline shell.

New checks: field units caught the water expense/cash-flow distinction; Firm versus subsidiary LCR prevented a wrong denominator context; native workbook reconciliation tests every registered result. See `PROGRESS.md` for executed test results and workbook engine limits.

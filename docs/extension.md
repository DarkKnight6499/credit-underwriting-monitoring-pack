# Credit pack extension

This extension adds solar project finance, a consumer warehouse, municipal analysis, issuer research, a Rule 2a-7 subset, and trade-price exception checks. It uses the existing `credit_pack.config.C` columns, ratio helper, Markdown tables, workbook layout, and pytest style. `extension_config.X` extends the shared column names; immutable dataclasses hold project, warehouse, and rule terms.

## Run and outputs

From the repository root:

```powershell
$env:PYTHONPATH="python;."
$env:PYTHONDONTWRITEBYTECODE="1"
New-Item -ItemType Directory -Force .work | Out-Null
& C:\Users\yazad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m credit_pack.run_extension --recalculate
& C:\Users\yazad\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q -p no:cacheprovider --basetemp=.work/pytest
```

The first command runs all six modules, writes CSVs and four issuer memos in `examples/output/`, and builds `excel/credit_extension.xlsx`. `--recalculate` requires LibreOffice and verifies native results before replacing the workbook with its recalculated copy. Without it, formulas are live but cached values are not verified. The original `run_all` remains separate. No new installed Python dependency is required beyond the existing project stack.

`data/extension/manifest.json` hashes the manually verified public selections. The output manifest hashes generated tables. The optional fetch script requires a descriptive `SEC_USER_AGENT` with an actual contact email. It saves raw documents separately and never rewrites selected facts automatically. Library and example runs do not fetch data.

## Methods

- **Solar project:** generation = MW x annual hours x capacity factor x degradation; revenue = generation x escalating price. CFADS deducts operating expense, illustrative cash tax, and maintenance contributions. Debt = min(PV of CFADS / target DSCR, capex x leverage cap). Annual service scales to the chosen debt. Negative amortization is rejected. Construction uses capex weights, equity first, half-month draw interest paid by equity, and equity-funded initial DSRA. Maintenance spending uses its funded account and is not deducted twice. DSRA targets half of next year's service, draws for deficits, tops up from surplus, and releases excess. Stress keeps principal fixed and changes revenue and interest.
- **Consumer warehouse:** seeded loans include balance, score, delinquency, term, APR, state, grade, verification, fraud, and default status. Hard exclusions precede concentration deductions. Both state and grade C caps use the same fixed pre-concentration pool denominator. State excess is allocated pro rata first; grade C excess applies to the remaining C collateral second. Final shares can differ from the input cap percentages because deductions shrink the pool. Grade advance rates apply afterward. Principal collections sweep debt, sponsor cash pays down next, and cash-limited cures preserve negative availability. Pool losses reduce collateral and never create paydown cash. Monthly covenants stop new draws. The final outstanding balance requires repayment or refinancing; no takeout financing is assumed.
- **Muni:** synthetic GO analysis measures fund balance, operating balance, debt/revenue, assessed-value burden, and collection rate. Revenue analysis measures CFADS, DSCR, cash days, and covenant break-even revenue decline. These use different repayment assumptions. TEY = exempt yield / (1 - assumed tax rate); taxable muni treatment is explicit. Comparators assume matched maturity, credit, and optionality, not actual comparable securities.
- **Issuer research:** four public historical selections cover Apple, JPMorgan Chase, Dutchess County GO context, and NYC Water revenue context. Each memo identifies risks, catalyst, monitoring triggers, score, and mock call. Public facts and synthetic spreads remain distinct. Two-factor scores provide a compact illustrative policy; published methodologies supply topics, not copied agency rating formulas.
- **Rule 2a-7:** fixed-rate WAM equals WAL within the supported subset. Individual checks do not substitute for portfolio checks or purchase restrictions. Buying a daily or weekly liquid asset can improve a liquidity shortfall without immediately curing it. The general issuer test aggregates reviewed issuer groups. Missing credit-risk review and unsupported structures require review. Parameters and omissions are mapped to primary text in `source_verification.md`.
- **Price validation:** linear interpolation of continuous zero rates plus a configured spread discounts full remaining coupons and principal. Dirty price less supplied accrued interest gives clean price per 100. Duration and convexity measure parallel continuous-rate sensitivity. Absolute differences strictly above tolerance flag breaks. Future/stale dates, cancellations, missing prices, and callable instruments require review. Inputs must contain one corrected surviving trade per security. No trade cleaning, option valuation, or dealer quotation service is claimed.

## Workbook scope

The dashboard links finished schedules. Inputs are unfilled cells on Assumptions and source schedules; formulas are visible in Excel's formula bar. Monthly pool balances and terms roll from initial loans. Eligibility, concentration haircuts, advance rates, certificates, draws, project reserves, sensitivity DSCR, muni ratios, TEY, fund metrics, and curve prices recalculate. Issuer scorecards are saved Python results and are labelled for rerun after fact edits. Rule acquisition logic and complex trade exception handling reside in Python. The workbook's price schedule supports the generated fixed coupon counts; rebuild after maturity or frequency edits.

## Limitations

Project production, costs, taxes, covenants, interest rates, consumer loans, servicing, losses, reserves, spreads, curves, and trade prices are synthetic. Default losses are stylized pro rata haircuts, not a validated loan-level credit model. Construction does not simulate permits, contractors, delays, or liquidated damages. No stochastic generation, hedging, tax equity, full interest waterfall, legal priority analysis, or actual lender execution is modelled.

Public issuer facts are manually selected historical data, not automated full filing analysis. Current detailed local-government criteria, specific GO and revenue bond pledges, tax status, EMMA disclosures, and real transaction prices were not verified. The money-market screen is deliberately partial and requires reviewed classifications, issuer aggregation, and board credit-risk inputs. No actual investment authority, compliance approval, vendor relationship, or real-world validation is claimed.

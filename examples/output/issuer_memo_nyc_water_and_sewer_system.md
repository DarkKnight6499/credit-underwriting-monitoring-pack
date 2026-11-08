# NYC Water and Sewer System: mock issuer memo

As of 2026-11-08. Model call: **HOLD**. This is an illustrative call on a synthetic bond scenario, not an instruction to trade.

The equally weighted two-factor score is 2.00 on a 1 (strongest) to 4 (weakest) scale. The offered spread is synthetic at 4 bp. Buy requires score at most 2 and spread at least 10 bp. Hold applies through score 2.5; a weaker score produces sell. Missing inputs require review. These bands are project policy, not agency ratings.

| factor | value | factor_score | weight |
| :-- | :-- | :-- | :-- |
| operating_margin_before_depreciation | 0.5110 | 1.0000 | 0.500 |
| debt_to_revenue | 7.5001 | 3.0000 | 0.500 |

The expense proxy excludes depreciation and includes O&M, administration, and other operating expenses. It is not a cash expense measure. Debt includes current and non-current bonds and notes. The report's coverage schedule nets carry-forwards and other adjustments, so this memo does not treat that figure as ordinary DSCR. Restricted cash is not assumed available. Bond-specific resolution coverage and EMMA disclosures remain unverified.

Risk: High debt burden, capital needs, affordability, and restricted cash. Catalyst: Require verified bond-specific coverage and sufficient spread before adding exposure. Monitoring: Operating margin below 30% or debt/revenue above 8x.

Sources: [FY2025 Annual Comprehensive Financial Report](https://www.nyc.gov/assets/nycwaterboard/downloads/pdf/statements_and_reports/wb-financial-statements-2025.pdf). Field lineage, retrieval date, selected units, methodology references, and unresolved checks are in `issuer_facts.csv` and `docs/source_verification.md`. Calls mix public historical facts with synthetic spreads. No market price, instrument recommendation authority, or real-world validation is claimed.

# Dutchess County: mock issuer memo

As of 2026-11-08. Model call: **SELL**. This is an illustrative call on a synthetic bond scenario, not an instruction to trade.

The equally weighted two-factor score is 3.00 on a 1 (strongest) to 4 (weakest) scale. The offered spread is synthetic at 15 bp. Buy requires score at most 2 and spread at least 10 bp. Hold applies through score 2.5; a weaker score produces sell. Missing inputs require review. These bands are project policy, not agency ratings.

| factor | value | factor_score | weight |
| :-- | :-- | :-- | :-- |
| fund_balance_ratio | 0.1381 | 2.0000 | 0.500 |
| operating_balance_ratio | -0.0201 | 4.0000 | 0.500 |

This is an issuer-level GO scenario. Financial inputs come from the County's release about its audited statements, not an EMMA disclosure. Revenue includes other financing sources; expense includes other uses. The fund balance ratio uses unassigned balance only. Bond-specific taxing authority, pledge, pension exposure, and legal remedies remain unverified.

Risk: General Fund deficit and declining unassigned balance; pensions and debt service are not reviewed. Catalyst: A restored operating surplus would support reconsideration. Monitoring: Further deficit, sales-tax weakness, or fund balance/revenue below 10%.

Sources: [Comptroller release of 2025 audited basic financial statements, 2026-10-02](https://www.dutchessny.gov/Departments/Comptroller/Independent-Audit-of-Basic-Financial-Statements-for-2025.htm). Field lineage, retrieval date, selected units, methodology references, and unresolved checks are in `issuer_facts.csv` and `docs/source_verification.md`. Calls mix public historical facts with synthetic spreads. No market price, instrument recommendation authority, or real-world validation is claimed.

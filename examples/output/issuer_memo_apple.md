# Apple: mock issuer memo

As of 2026-11-08. Model call: **HOLD**. This is an illustrative call on a synthetic bond scenario, not an instruction to trade.

The equally weighted two-factor score is 1.00 on a 1 (strongest) to 4 (weakest) scale. The offered spread is synthetic at 6 bp. Buy requires score at most 2 and spread at least 10 bp. Hold applies through score 2.5; a weaker score produces sell. Missing inputs require review. These bands are project policy, not agency ratings.

| factor | value | factor_score | weight |
| :-- | :-- | :-- | :-- |
| fcf_to_debt | 1.0011 | 1.0000 | 0.500 |
| total_leverage | 0.6816 | 1.0000 | 0.500 |

The debt measure includes current term debt, non-current term debt, and commercial paper. It excludes leases. EBITDA is operating income plus D&A under the existing pack convention. Historical cash flow supports the scenario, but the selected FY2025 statements are not a current surveillance update. Apple is the IG example; the rating reference and its scope are recorded in source_verification.md.

Risk: Product concentration, competition, and shareholder distributions. Catalyst: Review new annual cash flow and capital allocation before adding exposure. Monitoring: FCF/debt below 0.8 or leverage above 1.5x.

Sources: [2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm). Field lineage, retrieval date, selected units, methodology references, and unresolved checks are in `issuer_facts.csv` and `docs/source_verification.md`. Calls mix public historical facts with synthetic spreads. No market price, instrument recommendation authority, or real-world validation is claimed.

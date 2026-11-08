# JPMorgan Chase: mock issuer memo

As of 2026-11-08. Model call: **BUY**. This is an illustrative call on a synthetic bond scenario, not an instruction to trade.

The equally weighted two-factor score is 2.00 on a 1 (strongest) to 4 (weakest) scale. The offered spread is synthetic at 18 bp. Buy requires score at most 2 and spread at least 10 bp. Hold applies through score 2.5; a weaker score produces sell. Missing inputs require review. These bands are project policy, not agency ratings.

| factor | value | factor_score | weight |
| :-- | :-- | :-- | :-- |
| cet1_ratio | 0.1460 | 1.0000 | 0.500 |
| lcr | 1.1100 | 3.0000 | 0.500 |

The selected CET1 measure is year-end Standardized CET1. LCR is the Firm average, not the bank subsidiary or a year-end spot measure. No capital requirement, GSIB surcharge, TLAC, resolution recovery, or regulatory headroom is calculated.

Risk: Funding outflows, market risk, credit losses, and holding company structural subordination. Catalyst: Synthetic spread compensates for the two-factor score under the chosen policy. Monitoring: LCR below 1.05 or CET1 below 12%; these are scenario triggers, not regulatory minima.

Sources: [2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm). Field lineage, retrieval date, selected units, methodology references, and unresolved checks are in `issuer_facts.csv` and `docs/source_verification.md`. Calls mix public historical facts with synthetic spreads. No market price, instrument recommendation authority, or real-world validation is claimed.

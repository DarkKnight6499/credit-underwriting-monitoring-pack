
## Project finance, warehouse, and fixed income extension

The extension adds a synthetic solar project with construction funding, DSCR sculpting, DSRA and maintenance reserves, and a fixed-debt sensitivity grid. A seeded consumer warehouse includes loan eligibility, concentration deductions, grade advance rates, certificates, cash-limited paydowns, draw blocking, and monthly covenants.

Four issuer memos combine named public historical facts with synthetic spreads and illustrative buy/hold/sell policy. GO and revenue muni scenarios include distinct credit metrics, tax-equivalent yields, and relative value. A Rule 2a-7 subset uses verified current eCFR parameters. Curve-based price checks demonstrate synthetic TRACE/EMMA-shaped inputs; no actual TRACE/EMMA trade or EMMA disclosure was obtained.

```powershell
$env:PYTHONPATH="python;."
python -m credit_pack.run_extension --recalculate
```

Use the configured interpreter path in [extension instructions](docs/extension.md) if `python` is not on PATH. Results and mock memos are in `examples/output/`; the [live-formula workbook](excel/credit_extension.xlsx) is separate from the original workbook. [Mock term sheet](examples/output/mock_term_sheet.html) is formatted for one printed letter page. The source ledger records [verified text and failed routes](docs/source_verification.md). All added model inputs are in `python/credit_pack/extension_config.py` or clearly marked module config blocks. No runtime network access is needed.

Limitations: simplified renewable generation and reserve waterfalls; stylized consumer losses; two-factor issuer scores; historical manual public selections; unverified bond-specific muni pledges and tax status; incomplete Rule 2a-7 coverage; synthetic market prices. Native formula reconciliation and hand-computed tests establish mechanical agreement, not real-world validation.

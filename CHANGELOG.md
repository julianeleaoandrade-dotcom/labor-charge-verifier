# Changelog

All notable changes to this project are listed here. Versions follow
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-30

First public release.

### Added

- `lcv check-invoice`: eight checks of invoice lines against the contract
  roster, timesheets, payroll and contract unit prices (INV-01 to INV-08),
  reporting overbilled and underbilled amounts.
- `lcv check-wages`: four checks of payroll against the wage determination
  (WAGE-01 to WAGE-04), reporting amounts owed to workers.
- `lcv price-adjustment`: FAR 52.222-43 price-adjustment worksheet (PA-01 to
  PA-05) with a draft notice and a checklist of supporting records.
- Fictitious sample data with planted errors and `EXPECTED_FINDINGS.md`.
- Rules catalog, data format reference and a plain-language guide to
  FAR 52.222-43.
- Settings file with the source and access date of every regulatory value.
- Test suite and GitHub Actions workflow.

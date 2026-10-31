# Changelog

All notable changes to this project are listed here. Versions follow
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-10-31

### Added

- Browser version: a web page (`web/`), published with GitHub Pages, that runs
  the same Python package in the browser with Pyodide. No installation; the
  files a user selects are processed in the browser tab and are not uploaded.
- Blank CSV templates (`templates/`) for each input file.
- `scripts/build_site.py` and a GitHub Actions workflow (`pages.yml`) that runs
  the tests and publishes the page on every push to `main`.

### Changed

- CSV files saved by spreadsheet programs are read as well: UTF-8 with a
  byte-order mark, Windows-1252 encoding and semicolon-separated files.

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

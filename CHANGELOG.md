# Changelog

All notable changes to this project are listed here. Versions follow
[Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-10-31

### Added

- One Excel workbook (.xlsx) as input, as an alternative to separate CSV
  files: one worksheet per kind of record (Contract, Roster, Timesheets,
  Payroll, Invoice, Wage determination, Price adjustment). Works on the web
  page and on the command line (`--data workbook.xlsx`, `--input workbook.xlsx`).
- `templates/labor-charge-verifier-template.xlsx`: blank workbook with an
  instructions sheet, a note on every column header, date formats and
  date/LINE-TOTAL validation.
- `sample-data/sample-workbook.xlsx`: the sample data in the same layout; it
  gives the same findings as the CSV files.
- `scripts/build_workbooks.py` builds both workbooks from the CSV files.

### Changed

- The web page offers the workbook first ("Easiest way") and fills in every
  check from one file. Error messages name the worksheet instead of the CSV
  file when the data came from a workbook.
- Clear error when the contract or roster has no data rows.
- New dependency: `openpyxl` (MIT). The web page serves its wheel with the
  page instead of fetching it from another site.

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

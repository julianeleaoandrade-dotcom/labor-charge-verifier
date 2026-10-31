# Blank templates

**Easiest:** `labor-charge-verifier-template.xlsx`, one Excel workbook with an
instructions sheet and one worksheet per kind of record. Fill in the sheets
you need and choose the file on the web page (or pass it to `--data`).
A filled-in example with fictitious data is in
[sample-data/sample-workbook.xlsx](../sample-data/sample-workbook.xlsx).

**Alternative:** one CSV file per input. Each file has the column headers the
tool expects and no data. Fill in one row per record and save it as
**CSV (comma delimited)** or **CSV UTF-8**. Keep the header row unchanged.

| CSV file (worksheet) | One row per | Used by |
|---|---|---|
| contract.csv (Contract) | post and price period | invoice check, wage check |
| roster.csv (Roster) | employee | invoice check, wage check |
| timesheets.csv (Timesheets) | employee, post and day worked | invoice check |
| payroll.csv (Payroll) | employee and workweek | invoice check, wage check |
| invoice.csv (Invoice) | invoice line, plus one TOTAL row | invoice check |
| wage_determination.csv (Wage determination) | occupation on the wage determination | wage check |
| price_adjustment_input.csv (Price adjustment) | occupation | price adjustment |

Column meanings and examples: [docs/data-format.md](../docs/data-format.md).
Filled-in examples with fictitious data: [sample-data/](../sample-data/).

Use employee IDs, not names or Social Security numbers.

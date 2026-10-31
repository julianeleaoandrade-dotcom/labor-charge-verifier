# Blank templates

Each file has the column headers the tool expects and no data. Open a file in
Excel or another spreadsheet program, fill in one row per record, and save it
as **CSV (comma delimited)** or **CSV UTF-8**. Keep the header row unchanged.

| File | One row per | Used by |
|---|---|---|
| contract.csv | post and price period | invoice check, wage check |
| roster.csv | employee | invoice check, wage check |
| timesheets.csv | employee, post and day worked | invoice check |
| payroll.csv | employee and workweek | invoice check, wage check |
| invoice.csv | invoice line, plus one TOTAL row | invoice check |
| wage_determination.csv | occupation on the wage determination | wage check |
| price_adjustment_input.csv | occupation | price adjustment |

Column meanings and examples: [docs/data-format.md](../docs/data-format.md).
Filled-in examples with fictitious data: [sample-data/](../sample-data/).

Use employee IDs, not names or Social Security numbers.

# Data format

Blank templates for every file are in [templates/](../templates/).

All inputs are CSV files with a header row (UTF-8, with or without a
byte-order mark; Windows-1252 and semicolon-separated files saved by
spreadsheet programs are also read). Dates use `YYYY-MM-DD`.
Money is in US dollars with a dot as the decimal separator. Extra columns are
ignored, except in the price-adjustment input (see below).

Number columns may not be blank (a blank is an error, not a zero), except
`hours_billed` and `unit_price` on the invoice `TOTAL` row. `employee_id` must
be unique in the roster, `line_id` unique on invoice lines, and
(`employee_id`, `week_start`) unique in payroll. Problems are reported as a
plain error message naming the file and column.

Use employee IDs, not names or Social Security numbers. The tool never needs
an SSN.

`check-invoice` and `check-wages` read a folder (`--data`) containing the
files below. `price-adjustment` reads one file (`--input`).

## contract.csv

One row per post and price period.

| Column | Example | Meaning |
|---|---|---|
| contract_id | CTR-SAMPLE-0001 | Contract identifier |
| contractor_name | Example Facility Services LLC | Contractor |
| wd_number | SAMPLE-WD-0001 | Wage determination incorporated in the contract (one per contract) |
| post_id | P01 | Post or labor category |
| post_name | Day janitorial | Description |
| occupation_code | 11150 | WD occupation code for the post |
| required_headcount | 8 | Number of people the contract authorizes on the post |
| billing_unit | hour | Unit billed (this version supports hourly billing) |
| unit_price | 28.40 | Contract price per unit |
| price_effective_start | 2025-09-01 | First day this price applies |
| price_effective_end | 2026-02-14 | Last day this price applies |

## roster.csv

One row per employee assigned to the contract.

| Column | Example | Meaning |
|---|---|---|
| contract_id | CTR-SAMPLE-0001 | Contract identifier |
| employee_id | E001 | Employee ID (no SSN) |
| first_name, last_name | Avery, Holt | Optional; may be left blank or replaced with codes |
| occupation_code | 11150 | WD occupation code of the employee |
| occupation_title | Janitor | Occupation title |
| post_id | P01 | Usual post |
| hire_date | 2024-03-01 | First day employed on the contract |
| termination_date | 2026-02-14 | Last day employed; blank if still employed |

## timesheets.csv

One row per employee, post and day worked.

| Column | Example | Meaning |
|---|---|---|
| employee_id | E001 | Employee ID |
| post_id | P01 | Post worked |
| work_date | 2026-02-02 | Day worked |
| hours | 8 | Hours worked that day |

## payroll.csv

One row per employee and workweek. Workweeks are fixed 7-day periods that
start on the day set in `workweek.start_day` (Sunday in the example settings);
every `week_start` must fall on that day.

| Column | Example | Meaning |
|---|---|---|
| employee_id | E001 | Employee ID |
| week_start, week_end | 2026-02-01, 2026-02-07 | Workweek |
| regular_hours | 40 | Hours paid at the regular rate |
| overtime_hours | 0 | Hours paid at the overtime rate |
| paid_leave_hours | 0 | Paid vacation, holiday or sick hours (counted for H&W) |
| hourly_rate_paid | 17.50 | Regular hourly rate paid |
| overtime_rate_paid | 26.25 | Overtime hourly rate paid |
| hw_paid | 222.00 | Health and welfare paid for the week, in cash or as plan contributions |

## invoice.csv

One row per invoice line, plus one `TOTAL` row with the stated invoice total
in `line_amount`.

| Column | Example | Meaning |
|---|---|---|
| invoice_number | INV-2026-02-SAMPLE | Invoice number |
| invoice_period_start, invoice_period_end | 2026-02-01, 2026-02-28 | Billing period |
| line_type | LINE or TOTAL | Row type |
| line_id | L001 | Line identifier (`TOTAL` for the total row) |
| employee_id | E001 | Employee billed |
| post_id | P01 | Post billed |
| service_start, service_end | 2026-02-01, 2026-02-14 | Dates covered by the line |
| hours_billed | 80 | Hours billed |
| unit_price | 28.40 | Unit price billed |
| line_amount | 2272.00 | Amount billed on the line (or stated total on the TOTAL row) |

## wage_determination_*.csv

Exactly one file per data folder whose name starts with `wage_determination`,
holding one revision of the WD (the one incorporated in the contract).
Lines starting with `#` are comments (the sample uses them for its SAMPLE
banner). Copy the rates from the official WD on sam.gov that is incorporated
in your contract.

| Column | Example | Meaning |
|---|---|---|
| wd_number | SAMPLE-WD-0001 | WD number (must match contract.csv) |
| revision | 1 | WD revision |
| state, area | ZZ, Sample County | Locality |
| occupation_code | 11150 | Occupation code |
| occupation_title | Janitor | Occupation title |
| hourly_rate | 17.20 | Minimum hourly wage rate |

The H&W rate is set in `config/settings.yaml` (`health_and_welfare.rate_per_hour`).

## price_adjustment_input.csv

One row per occupation. Columns whose names contain overhead, G&A, general
and administrative, indirect, profit, fee or markup are refused (rule PA-04).

| Column | Example | Meaning |
|---|---|---|
| contract_id | CTR-SAMPLE-0001 | Contract identifier |
| occupation_code, occupation_title | 11150, Janitor | Occupation |
| prior_wd_rate | 17.20 | Wage rate on the prior WD |
| new_wd_rate | 17.85 | Wage rate on the new WD |
| prior_rate_paid | 17.50 | Rate actually paid before the new WD |
| new_rate_paid | 17.85 | Rate actually paid after the new WD |
| prior_hw_rate | 5.55 | H&W rate on the prior WD |
| new_hw_rate | 5.92 | H&W rate on the new WD |
| prior_hw_paid | 5.55 | H&W actually paid per hour before the new WD (cash or plan contributions) |
| new_hw_paid | 5.92 | H&W actually paid per hour after the new WD |
| hours | 24960 | Hours the adjustment applies to (for example the option year) |
| wd_received_date | 2026-09-15 | Date the new WD was received |

## Outputs

`check-invoice` and `check-wages` write three files each to `--out`:

- `*_findings.csv` - one row per finding with `rule_id`, `rule_title`,
  `severity`, `direction`, `module`, `employee_id`, `post_id`, `line_id`,
  `period`, `billed_amount`, `expected_amount`, `difference`,
  `amount_owed_to_worker` and `description`.
- `*_report.md` and `*_report.html` - the same findings with a summary of totals
  in each direction.

For wage findings, `billed_amount` holds what was paid (a rate or an amount)
and `expected_amount` what was required. For INV-03, they hold payroll and
timesheet hours valued at the rate paid.

`price-adjustment` writes:

- `price_adjustment_worksheet.csv` - one row per occupation with every step of
  the calculation.
- `price_adjustment_summary.md` - totals, the notice deadline and warnings.
- `price_adjustment_notice_DRAFT.md` - a generic draft notice to the
  contracting officer with fields in square brackets to fill in.
- `price_adjustment_supporting_documents.md` - a checklist of records to attach
  and keep.

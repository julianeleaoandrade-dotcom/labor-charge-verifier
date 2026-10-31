# Expected findings for the sample data

All data in this folder is fictitious. "Example Facility Services LLC", contract
`CTR-SAMPLE-0001`, the employees and the wage determination `SAMPLE-WD-0001`
were invented for testing. The wage determination file is marked
**SAMPLE - NOT A REAL WAGE DETERMINATION**.

## What the sample contains

- One fictitious janitorial and security contract with three posts:

  | Post | Description | Occupation | Headcount | Price to 2026-02-14 | Price from 2026-02-15 |
  |---|---|---|---:|---:|---:|
  | P01 | Day janitorial | Janitor (11150) | 8 | 28.40 | 29.10 |
  | P02 | Night janitorial | Janitor (11150) | 4 | 30.20 | 30.90 |
  | P03 | Security guard | Guard I (27101) | 6 | 34.50 | 35.30 |

- 20 employees (`E001` to `E020`). `E017` left on 2026-02-14; `E019` and
  `E020` started on 2026-02-15.
- One month of service: February 2026, which runs Sunday 2026-02-01 to Saturday
  2026-02-28, so it holds exactly four Sunday-to-Saturday workweeks.
- Daily timesheets, weekly payroll, one invoice (`INV-2026-02-SAMPLE`) with
  one line per employee and price period, and a price-adjustment input for
  the next option year.
- The unit prices change in the middle of the month (2026-02-15).

`sample-workbook.xlsx` holds the same data as the CSV files, one worksheet
per file, and gives exactly the same findings.

The errors below were planted on purpose. Running the commands in the README
must produce these findings and no others. The test suite checks this
(`tests/test_invoice_check.py`, `tests/test_wage_check.py`,
`tests/test_price_adjustment.py`).

## `lcv check-invoice --data sample-data --out reports/`

14 findings: 8 overbilled (USD 10,941.20), 3 underbilled (USD 1,303.20) and
1 worker paid less than recorded (USD 70.00).

| # | Rule | Employee | Post | Line | What was planted | Direction | Difference (USD) |
|---:|---|---|---|---|---|---|---:|
| 1 | INV-01 | E017 | P01 | L036 | Billed for 2026-02-15 to 2026-02-28 after leaving on 2026-02-14 | overbilled | 2,328.00 |
| 2 | INV-01 | E099 | P03 | L041 | Billed employee who is not on the roster | overbilled | 2,760.00 |
| 3 | INV-02 | E003 | P01 | L005 | 88 hours billed; timesheets show 80 | overbilled | 227.20 |
| 4 | INV-02 | E010 | P02 | L021 | 72 hours billed; timesheets show 80 (in the client's favor) | underbilled | -247.20 |
| 5 | INV-02 | E011 | P03 | L023 | 80 hours billed on a post with no timesheet hours | overbilled | 2,760.00 |
| 6 | INV-03 | E007 | | | Week of 2026-02-15: payroll pays 36 hours; timesheets show 40 | underpaid_worker | owed 70.00 |
| 7 | INV-04 | E005 | P01 | L010 | Old unit price 28.40 billed after the change to 29.10 (stale price, in the client's favor) | underbilled | -56.00 |
| 8 | INV-05 | | P01 | | 9 employees billed on each day from 2026-02-15 to 2026-02-28; contract authorizes 8 | overbilled | (no amount) |
| 9 | INV-05 | | P03 | | 7 employees billed on each day from 2026-02-01 to 2026-02-14 (because of line L023); contract authorizes 6 | overbilled | (no amount) |
| 10 | INV-06 | E008 | P02 | L016 | Exact duplicate of line L015 | overbilled | 2,416.00 |
| 11 | INV-06 | E011 | P03 | L023 | Same person billed on P02 (L022) and P03 (L023) for the same dates | none | (see #5) |
| 12 | INV-07 | E013 | P03 | L028 | Start 2026-02-28, end 2026-02-15: a day count of -12 ("negative days") | none | (cannot verify) |
| 13 | INV-08 | | | TOTAL | Stated total is 1,000.00 less than the sum of the lines (in the client's favor) | underbilled | -1,000.00 |
| 14 | INV-08 | E006 | P01 | L011 | Line amount 2,722.00; 80 hours x 28.40 = 2,272.00 (transposed digits) | overbilled | 450.00 |

Errors in both directions are present: in the contractor's favor (for example
#2, #3, #10, #14) and in the client's favor (#4, #7, #13).

Notes on how rules interact:

- A line that fails INV-01, INV-06 (duplicate or same-post overlap) or INV-07
  is not checked again by INV-02 and INV-04, so the same dollars are not
  counted twice.
- When INV-02 and INV-04 both apply to one line, INV-02 values the hours
  difference at the billed price and INV-04 values the price difference on the
  hours the timesheets support, so the two amounts add up to the true
  difference.
- Line L028 (#12) is still counted toward P03 headcount, using its dates in the
  right order, so a date typo does not create a false staffing finding.
- #11 has no amount because the amount is already reported by #5.

## `lcv check-wages --data sample-data --out reports/`

10 findings; USD 217.60 owed to workers.

| Rule | Employee | Weeks | What was planted | Owed to worker (USD) |
|---|---|---|---|---:|
| WAGE-01 | E004 | all 4 weeks | Paid 16.80/hour; sample WD rate for Janitor is 17.20 | 4 x 16.00 = 64.00 |
| WAGE-02 | E009 | all 4 weeks | H&W paid at 5.09/hour instead of the configured 5.55/hour (40 hours x 0.46) | 4 x 18.40 = 73.60 |
| WAGE-03 | E015 | 2026-02-08 to 2026-02-14 | 48 hours paid at straight time; 8 hours needed 1.5 x 20.00 | 80.00 |
| WAGE-04 | E019 | all weeks | Occupation "Custodial Team Lead" (LEAD-01) is not on the sample WD; conformance may be needed | (not calculated) |

E007's short payroll week (#6 above) is not repeated here: the wage check
tests the rate paid and the hours on the payroll, while INV-03 compares payroll
hours with timesheets.

## `lcv price-adjustment --input sample-data/price_adjustment_input.csv --out reports/`

| Occupation | Prior WD | New WD | Paid before | Paid after | Allowable / hour | Why |
|---|---:|---:|---:|---:|---:|---|
| Janitor (11150) | 17.20 | 17.85 | 17.50 | 17.85 | 0.35 | Already paid above the prior WD; only 17.85 - 17.50 is allowable |
| Laborer, Grounds Maintenance (11210) | 18.05 | 18.60 | 18.05 | 18.60 | 0.55 | Paid exactly the WD before and after |
| Guard I (27101) | 19.40 | 20.10 | 20.00 | 20.50 | 0.10 | Same logic as the FAR 52.222-43(d) example: 20.10 - 20.00; the rest of the raise is voluntary |

- H&W increase: the sample contractor paid exactly the WD H&W rate before
  (5.55) and after (5.92), so 0.37/hour is allowable on every occupation.
- Payroll taxes and insurance: 14.45% of the wage increase (6.2 + 1.45 + 0.6 +
  2.7 + 3.5, from `config/settings.example.yaml`; the last two are example rates).
- Total adjustment: **USD 27,358.40**. No overhead, G&A or profit.
- WD received 2026-09-15, so the notice was due 2026-10-15. Run on any date
  after that, the tool reports the deadline as **passed** and prints a warning.
  Use `--as-of 2026-10-01` to see the same input with 14 days left.

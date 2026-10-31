# Rules catalog

Each rule has an ID that appears on every finding it produces. The short form
of this catalog is in `src/labor_charge_verifier/rules.py`.

A finding is a lead for a person to review. The tool does not decide whether
a charge is allowable or whether a law was violated.

**Directions** used in findings:

| Direction | Meaning |
|---|---|
| `overbilled` | The invoice charges more than the records support. |
| `underbilled` | The invoice charges less than the records support. |
| `underpaid_worker` | The worker was paid less than required or recorded. `amount_owed_to_worker` is filled in. |
| `overpaid_worker` | Payroll pays more hours than the timesheets record. |
| `none` | A control issue with no direct dollar direction. |

Sources were accessed on 2026-10-30. Links are listed at the end.

---

## Module 1 - Invoice vs. records (`lcv check-invoice`)

### INV-01 - Billed employee is on the roster and active (high)

- **Checks:** the employee on each invoice line is on the contract roster and
  was employed (from hire date to termination date) on every day of the
  billed service period.
- **Why:** a charge for someone who was not on the contract, or not employed
  on those days, has no work behind it.
- **Amount:** if the employee was not active on any billed day, the expected
  amount is zero. If active for part of the period, the expected amount is the
  timesheet hours inside the active dates times the billed unit price.
- **Basis:** for federal awards, charges for salaries and wages must be based
  on records that accurately reflect the work performed [2 CFR 200.430(g)(1)].
  For contracts, the contract's payment terms.

### INV-02 - Billed hours match timesheets (high)

- **Checks:** hours billed on each line equal the timesheet hours for the same
  employee, post and dates, within `tolerances.hours` (default 0.25 hours).
- **Why:** this is the core test that a billed hour was worked. It finds errors
  in both directions.
- **Amount:** (billed hours - timesheet hours) x billed unit price.
- **Basis:** 2 CFR 200.430(g)(1); contract payment terms.

### INV-03 - Hours paid on payroll match timesheets (medium)

- **Checks:** for each employee and workweek, regular plus overtime hours on
  payroll equal the hours on timesheets. Also flags timesheet weeks with no
  payroll record. Workweeks start on `workweek.start_day`; payroll weeks must
  start on that day.
- **Why:** payroll is the evidence of the labor cost behind a charge. When
  payroll pays fewer hours than were worked, the worker may be owed money.
- **Amount:** when payroll is short, `amount_owed_to_worker` = missing hours x
  rate paid (straight time only; any overtime premium must be reviewed).
- **Basis:** 2 CFR 200.430(g)(1); contractors on covered contracts must keep
  records of hours worked and pay [29 CFR 4.6(g)].

### INV-04 - Unit price is the contract price in effect on the service date (high)

- **Checks:** the unit price on each line equals the contract price for that
  post on the service dates. A line that crosses a price change is flagged so
  it can be split; its expected price is weighted by the hours worked each day.
- **Why:** after a price change, an old price left in a billing template
  produces an error, in either direction, on every invoice until it is caught.
- **Amount:** (billed unit price - contract unit price) x the hours the
  timesheets support. INV-02 values the hours difference at the billed price,
  so when both rules fire on one line their amounts add up to the billed amount
  minus the supported amount, with no dollar counted twice.
- **Basis:** contract pricing terms.

### INV-05 - Billed headcount per post matches the contract (medium)

- **Checks:** for each day, the number of distinct employees billed to a post,
  compared with the contract's required headcount on that day. Consecutive days
  with the same result are reported as one finding. More than
  authorized is reported as `overbilled` (to be confirmed); fewer is reported
  with severity `low` as a staffing item to confirm.
- **Why:** records can agree with each other and still describe more positions
  than the contract pays for.
- **Amount:** none. The rule reports the count; the dollar effect depends on
  whether the extra position was authorized.
- **Basis:** contract staffing terms.

### INV-06 - No duplicate lines and no employee on two posts at once (high)

- **Checks:** (a) exact duplicate lines; (b) the same employee on two lines
  with overlapping dates, either on the same post or on different posts.
- **Why:** a repeated line or a person billed twice for the same time are
  charges with no separate work behind them.
- **Amount:** for a duplicate, or an overlap on the same post, the full amount
  of the later line (the timesheet hours can support only one of them). For an
  overlap on different posts, no amount here; INV-02 reports the hours the
  timesheets for each post do not support.
- **Basis:** contract payment terms; 2 CFR 200.430(g)(1).

### INV-07 - Service dates are valid (high)

- **Checks:** start date on or before end date (no negative day count), both
  dates present, and dates inside the invoice period.
- **Why:** date formulas that subtract the wrong way produce "negative days"
  and make the charge impossible to verify.
- **Amount:** none; the line must be corrected before it can be checked.
- **Basis:** accuracy of the claim for payment.

### INV-08 - Line amounts and invoice total recalculate (medium)

- **Checks:** each line amount equals hours x unit price (within
  `tolerances.money`), and the stated invoice total equals the sum of the
  stated line amounts.
- **Why:** transposed digits and broken spreadsheet totals are common and easy
  to catch.
- **Amount:** stated amount - recalculated amount.
- **Basis:** accuracy of the claim for payment.

---

## Module 2 - Wage-determination compliance (`lcv check-wages`)

The same records that stop an hour billed in excess also show when a worker
was paid less than required. Every underpayment is reported with
`amount_owed_to_worker`.

### WAGE-01 - Hourly rate paid is at least the wage determination rate (high)

- **Checks:** the hourly rate paid is at least the rate in the contract's wage
  determination (WD) for the employee's occupation.
- **Amount owed:** (WD rate - rate paid) x straight-time and paid leave hours,
  plus (WD rate - rate paid) x 1.5 x overtime hours.
- **Basis:** service employees on covered contracts must be paid not less than
  the wage rates in the WD [41 U.S.C. 6703; 29 CFR 4.6; FAR 52.222-41].

### WAGE-02 - Health and welfare (H&W) benefit is at least the required amount (high)

- **Checks:** H&W paid in the week (cash or plan contributions) is at least
  `health_and_welfare.rate_per_hour` x hours paid, capped at
  `health_and_welfare.weekly_hour_cap` (40).
- **Hours basis:** with `basis: hours_paid` (default), hours paid include
  regular, overtime and paid leave hours, up to 40 per week. With
  `basis: hours_worked`, paid leave is left out. The 2,080-hour annual cap is
  not modeled.
- **Amount owed:** required H&W - H&W paid.
- **Basis:** H&W is due for all hours paid for, including paid vacation, sick
  leave and holiday hours, up to 40 hours per week and 2,080 hours per year on
  each contract [29 CFR 4.175(a)]. DOL sets the rate in All Agency Memoranda:
  $5.55/hour under AAM 250 (2025) and $5.92/hour under AAM 252 (2026), with
  lower rates for contracts subject to Executive Order 13706 and for Hawaii.
  The rate that applies is the one on the WD incorporated in the contract.

### WAGE-03 - Overtime over 40 hours per week is paid at 1.5 times the rate (high)

- **Checks:** for each workweek, hours over 40 are paid at not less than 1.5 x
  the hourly rate paid. Catches both overtime recorded as regular hours and an
  overtime rate below 1.5x.
- **Simplification:** the "regular rate" is taken to be the hourly rate paid.
  Other pay that must be included in the regular rate, alternative overtime
  systems and exemptions are out of scope.
- **Amount owed:** required pay for the week - actual pay for the week.
- **Basis:** 29 U.S.C. 207(a)(1).

### WAGE-04 - Employee's occupation is listed on the wage determination (medium)

- **Checks:** the employee's occupation code is on the contract's WD.
- **What the tool does:** if not, it reports that a conformance request may be
  needed and skips WAGE-01 for that employee. It does not calculate a
  conformed rate, because that requires a decision by the contracting officer
  and DOL.
- **Basis:** classes of service employees not listed on the WD must be
  classified by conformance [29 CFR 4.6(b)(2); FAR 52.222-41(c)(2)].

---

## Module 3 - FAR 52.222-43 price-adjustment worksheet (`lcv price-adjustment`)

### PA-01 - Allowable wage increase per occupation (high)

- **Calculation:** allowable increase = the lower of (a) the actual increase in
  the rate paid and (b) the increase needed to bring the rate previously paid
  (or the prior WD rate, if higher) up to the new WD rate. Never below zero.
- **Decreases:** the clause also covers decreases, which must be reported
  promptly (paragraphs (d) and (f)). This worksheet computes increases only and
  adds a note when a decrease appears in the input.
- **Check against the clause:** the clause's example in paragraph (d)(1) - prior WD $4.00,
  contractor paid $4.10, new WD $4.50, contractor raises pay to $4.75 - gives
  $0.40 per hour. The test suite verifies this exact example.
- **Basis:** FAR 52.222-43(d).

### PA-02 - Health and welfare increase (medium)

- **Calculation:** the same rule as PA-01, applied to H&W per hour: the lower
  of the actual increase in H&W paid and the increase needed to bring the H&W
  previously paid (or the prior WD H&W rate, if higher) up to the new WD H&W
  rate, times hours.
- **Basis:** FAR 52.222-43(d) adjusts for the actual increase in wages and
  fringe benefits made to comply with the new WD.

### PA-03 - Accompanying payroll taxes and insurance (medium)

- **Calculation:** wage increase x the sum of the rates in
  `payroll_tax_rates` (Social Security, Medicare, FUTA, SUTA, workers'
  compensation). H&W is added to the base only if
  `apply_taxes_to_health_and_welfare` is true.
- **Basis:** FAR 52.222-43(e) includes the accompanying increases in Social
  Security and unemployment taxes and workers' compensation insurance.

### PA-04 - No overhead, G&A or profit (high)

- **Checks:** refuses input whose column names contain overhead, G&A, general
  and administrative, indirect, profit, fee or markup (list in
  `price_adjustment.forbidden_cost_terms`), and explains why.
- **Basis:** FAR 52.222-43(e) excludes general and administrative costs,
  overhead and profit.

### PA-05 - 30-day notice deadline (high)

- **Calculation:** deadline = date the new WD was received + 30 days. Status is
  `open` or `passed` as of today (or `--as-of`).
- **Basis:** FAR 52.222-43(f) requires notice of an increase claimed within 30
  days of receipt of the new WD, unless the contracting officer extends the
  period in writing.

---

## Sources (accessed 2026-10-30)

- 2 CFR 200.430, Compensation - personal services: <https://www.ecfr.gov/current/title-2/section-200.430>
- 29 CFR 4.6, Labor standards clauses for Federal service contracts: <https://www.ecfr.gov/current/title-29/section-4.6>
- 29 CFR 4.175, Meeting requirements for health, welfare, and/or pension benefits: <https://www.ecfr.gov/current/title-29/section-4.175>
- 41 U.S.C. 6703, Required contract terms: <https://www.law.cornell.edu/uscode/text/41/6703>
- 29 U.S.C. 207, Maximum hours: <https://www.law.cornell.edu/uscode/text/29/207>
- FAR 52.222-41, Service Contract Labor Standards: <https://www.acquisition.gov/far/52.222-41>
- FAR 52.222-43, Fair Labor Standards Act and Service Contract Labor Standards - Price Adjustment (Multiple Year and Option Contracts): <https://www.acquisition.gov/far/52.222-43>
- DOL Wage and Hour Division, All Agency Memoranda (AAM 250, AAM 252): <https://sam.gov/content/wage-determinations/resources/all-agency-memos>

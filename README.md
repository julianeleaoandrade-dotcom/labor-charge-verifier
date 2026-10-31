# labor-charge-verifier

Open-source checks that labor charges on service contracts are backed by
payroll, timekeeping and contract or wage-determination rates before an
invoice is submitted.

**Try it in your browser, no installation:**
**<https://julianeleaoandrade-dotcom.github.io/labor-charge-verifier/>**

[![tests](https://github.com/julianeleaoandrade-dotcom/labor-charge-verifier/actions/workflows/tests.yml/badge.svg)](https://github.com/julianeleaoandrade-dotcom/labor-charge-verifier/actions/workflows/tests.yml)
![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)

## Who it is for

- **Small and mid-sized service contractors** on federal contracts covered by
  the Service Contract Act (janitorial, security, facility support and
  similar), who want to check an invoice before it goes out.
- **Recipients of federal grants** who charge salaries and wages to an award
  and need those charges to match their time and payroll records.
- **Auditors and reviewers** who examine either of the above.

## Why it matters

- Federal agencies estimated about $186 billion in improper payments in fiscal
  year 2025, most of them overpayments
  ([GAO-26-108694](https://www.gao.gov/products/gao-26-108694)).
- In fiscal years 2014 through 2019, the Department of Labor completed over
  5,000 Service Contract Act cases and found violations, primarily of wage and
  benefit protections, in 68 percent of them
  ([GAO-21-11](https://www.gao.gov/products/gao-21-11)).
- For federal awards, charges for salaries and wages must be based on records
  that accurately reflect the work performed
  ([2 CFR 200.430(g)(1)](https://www.ecfr.gov/current/title-2/section-200.430)).

The same comparison of records that stops an hour billed without work behind
it also finds a worker who was paid less than the wage determination requires.
This tool reports both, along with charges the contractor left off the
invoice: the goal is accuracy, not only cutting amounts.

## What it checks

Full descriptions, reasons and sources: [docs/rules-catalog.md](docs/rules-catalog.md).

**Module 1 - Invoice vs. records** (`lcv check-invoice`)

| Rule | Check |
|---|---|
| INV-01 | Billed employee is on the contract roster and was employed on the billed dates |
| INV-02 | Billed hours match timesheets (configurable tolerance) |
| INV-03 | Hours paid on payroll match timesheets |
| INV-04 | Unit price is the contract price in effect on the service date (finds stale prices) |
| INV-05 | Billed headcount per post matches the contract |
| INV-06 | No duplicate lines and no employee billed to two posts at once |
| INV-07 | Service dates are valid (no negative day counts, inside the invoice period) |
| INV-08 | Line amounts and the invoice total recalculate |

**Module 2 - Wage-determination compliance** (`lcv check-wages`)

| Rule | Check |
|---|---|
| WAGE-01 | Hourly rate paid is at least the wage determination (WD) rate for the occupation |
| WAGE-02 | Health and welfare (H&W) paid is at least the required amount per hour paid, up to 40 hours a week |
| WAGE-03 | Hours over 40 in a workweek are paid at 1.5 times the rate (basic rule only) |
| WAGE-04 | Employee's occupation is listed on the WD (if not, flags a possible conformance request) |

Every underpayment is reported with `amount_owed_to_worker`.

**Module 3 - FAR 52.222-43 price-adjustment worksheet** (`lcv price-adjustment`)

| Rule | Step |
|---|---|
| PA-01 | Allowable wage increase = the lower of the actual increase and the increase needed to reach the new WD, as in the clause's own example |
| PA-02 | Adds the allowable H&W increase, using the same rule as PA-01 |
| PA-03 | Adds accompanying Social Security, Medicare, unemployment taxes and workers' compensation insurance (rates from the configuration file) |
| PA-04 | Refuses overhead, G&A and profit, and explains why |
| PA-05 | Computes the 30-day notice deadline and warns if it has passed |

It writes a worksheet, a generic draft notice to the contracting officer and a
checklist of supporting records. A plain-language guide to the clause is in
[docs/far-52-222-43-guide.md](docs/far-52-222-43-guide.md).

## Try it in your browser

Open **<https://julianeleaoandrade-dotcom.github.io/labor-charge-verifier/>**,
choose a check, click **Use sample data** and then **Run**. To check your own
records, download the blank templates from the page (or from
[templates/](templates/)), fill them in Excel, save them as CSV and select them
on the page.

The page runs the same Python code as the command-line tool, inside the
browser tab. The files you select are not uploaded or sent anywhere. The first
time, the page downloads the open-source Python runtime
([Pyodide](https://pyodide.org)) from a public content network, which takes
about 20 seconds.

## Quick start (command line)

Requires Python 3.11 or later.

```bash
git clone https://github.com/julianeleaoandrade-dotcom/labor-charge-verifier.git
cd labor-charge-verifier
pip install -e .
lcv check-invoice --data sample-data --out reports/
lcv check-wages   --data sample-data --out reports/
lcv price-adjustment --input sample-data/price_adjustment_input.csv --out reports/
pip install -e ".[dev]"
pytest
```

The sample data is fictitious and contains errors planted on purpose; they are
listed in [sample-data/EXPECTED_FINDINGS.md](sample-data/EXPECTED_FINDINGS.md).
Excerpt of `reports/invoice_check_report.md` produced from the sample data:

| Measure | Count | Amount (USD) |
|---|---:|---:|
| Findings (high / medium / low) | 14 (9 / 5 / 0) | |
| Overbilled: charges the records do not support | 8 | 10,941.20 |
| Underbilled: supported work left off the invoice | 3 | 1,303.20 |
| Workers paid less than required or recorded | 1 | 70.00 |

| Rule | Direction | Employee | Line | Difference | Description |
|---|---|---|---|---:|---|
| INV-02 | overbilled | E003 | L005 | 227.20 | Billed 88 hours; timesheets show 80 hours for this employee, post and period. |
| INV-02 | underbilled | E010 | L021 | -247.20 | Billed 72 hours; timesheets show 80 hours for this employee, post and period. |
| INV-04 | underbilled | E005 | L010 | -56.00 | Billed unit price 28.40; contract price in effect for these dates is 29.10. Difference valued on 80 hours supported by timesheets. |
| INV-07 | none | E013 | L028 | | Service end date is before the start date, giving a day count of -12. The charge cannot be verified until the dates are corrected. |

Each report is written as CSV, Markdown and HTML. Input columns are described
in [docs/data-format.md](docs/data-format.md).

### Using your own data

1. Copy `config/settings.example.yaml` to `config/settings.yaml`.
2. Review **every** value, in particular the H&W rate (use the rate on the WD
   incorporated in your contract) and your own unemployment and workers'
   compensation rates. Each value records its source and access date.
3. Put your CSV files in a folder using the formats in
   [docs/data-format.md](docs/data-format.md), copying WD rates from the
   official WD on [sam.gov](https://sam.gov/wage-determinations).
4. Run the commands with `--data your-folder`.

## Design principles

- **Written, explainable rules.** Every check is a plain rule with an ID, a
  reason and a source. There is no scoring model.
- **Every finding shows why.** Each finding names its rule, the amount billed,
  the amount expected and the difference.
- **A person decides.** Findings are leads for review. Cases that need
  judgment (an extra position, an unlisted occupation, a late notice) are
  flagged, not resolved.
- **Local only.** The command-line tool runs on your computer, reads CSV files
  and writes files. The browser version processes files inside the browser tab.
  Neither sends your data to anyone.
- **Configuration, not code.** Rates that change (H&W, taxes, tolerances) live
  in the settings file, each with its source and date.

## Limitations

- It does not replace the contract, the official wage determination, the
  contracting officer or an attorney.
- It does not cover Davis-Bacon (construction) wage requirements, collective
  bargaining agreements under section 4(c) of the Service Contract Act,
  vacation and holiday benefits, or special overtime cases (other pay in the
  regular rate, alternative overtime systems, exemptions).
- The annual 2,080-hour H&W cap and tax wage bases are not modeled.
- It handles hourly billing. Fixed monthly prices per post need adapting.
- The price-adjustment worksheet computes increases only. Decreases must also
  be reported to the contracting officer (FAR 52.222-43(f)).
- Configuration values must be kept current by the user.

## Data privacy

Use anonymized data. Identify employees by an ID, not a Social Security
number. Never commit Social Security numbers, real names or other personal
data to this repository or to a fork of it. The `.gitignore` excludes the
`reports/` folder and `config/settings.yaml` so local results and settings are
not committed by accident.

## About the author

Built by Juliane Leão Andrade, a financial manager with eight years of
experience auditing labor billing, payroll and wage-driven price adjustments
for labor-intensive service contracts.

Developed with AI-assisted coding tools; the rules, method, test cases and final review are by the author.

## License and contributing

MIT License; see [LICENSE](LICENSE). Contributions are welcome; see
[CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in
[CHANGELOG.md](CHANGELOG.md).

# Preparing a price adjustment under FAR 52.222-43: a plain-language guide

> **This guide is general information, not legal or accounting advice. Always read your contract and the current FAR text.**

This guide is for the owner or manager of a small service contractor without a
legal department. It explains, step by step, how to prepare a price
adjustment request when a new wage determination takes effect on your
contract. The worksheet in this repository (`lcv price-adjustment`) does the
arithmetic described here.

Everything below is based on the text of the clause and the other sources
listed at the end. Where your contract says something different, your
contract controls.

## 1. When the clause applies

FAR 52.222-43, *Fair Labor Standards Act and Service Contract Labor
Standards - Price Adjustment (Multiple Year and Option Contracts)*, goes into
service contracts that contain the Service Contract Labor Standards clause
(FAR 52.222-41) and are **multiple-year contracts or contracts with options to
renew**. FAR 22.1006(c)(1) tells contracting officers to use it in
fixed-price, time-and-materials and labor-hour service contracts of that kind
above the simplified acquisition threshold, and allows its use below it.

Check your contract: if FAR 52.222-43 is listed in the clauses section, this
guide applies. If your contract instead has FAR 52.222-44 (contracts without
options) or an agency-specific clause, read that clause.

Note on the FAR overhaul (status as of October 2026): since late 2025, many
agencies have issued class deviations that rewrite FAR Part 22 in plainer
language and move guidance on wage determinations to a "FAR Companion" (for
example, U.S. Department of State Acquisition Alert 26-14). FAR 52.222-43 is
still published at acquisition.gov. Whatever clause text is in your contract
is what governs your request.

## 2. What changes when a new wage determination is issued

The Department of Labor's Wage and Hour Division issues **wage determinations
(WDs)** that set minimum hourly wages and fringe benefits for each occupation
in a locality. They are published on **sam.gov** (Wage Determinations
section).

Under paragraph (c) of the clause, the WD current on the **anniversary date**
of a multiple-year contract, or at the **start of each option period**,
applies to your contract. When that WD raises the minimum wage or benefits for
your workers, you must pay at least the new amounts, and paragraph (d) lets
the contract price be adjusted for the increase you actually pay to comply.

The adjustment works in both directions: paragraph (d) also covers decreases,
and paragraph (f) says decreases must be reported to the contracting officer
promptly. This guide and the worksheet focus on increases.

The health and welfare (H&W) fringe benefit rate also changes about once a
year. DOL announced $5.55 per hour in All Agency Memorandum 250 (2025) and
$5.92 per hour in All Agency Memorandum 252 (2026), with different rates for
contracts subject to Executive Order 13706 and for Hawaii. Use the H&W rate
printed on the WD that is actually incorporated in your contract.

## 3. Step by step

### Step 1: Put the two wage determinations side by side

Get the **prior WD** (the one in effect before the anniversary or option date)
and the **new WD** incorporated in your contract. For each occupation you
employ on the contract, write down:

- the wage rate on the prior WD;
- the wage rate on the new WD;
- the H&W rate on each WD.

Also write down the H&W you actually paid per hour before and after (in cash
or as plan contributions).

### Step 2: Write down what you actually paid

From your payroll records, write down for each occupation:

- the rate you **actually paid before** the new WD; and
- the rate you **actually pay after** the new WD.

Use payroll records, not plans or budgets. Paragraph (f) asks for supporting
data, including payroll records.

### Step 3: Calculate the allowable wage increase

Paragraph (d) adjusts the price for your **actual increase** in wages to
comply with the new WD. That means the allowable increase per hour is the
**lower** of:

- (a) how much you actually raised the rate; and
- (b) how much you needed to raise it to reach the new WD rate, starting from
  what you were already paying.

The clause gives this example in paragraph (d)(1):

| | Rate |
|---|---:|
| Prior WD minimum | $4.00 |
| What the contractor actually paid | $4.10 |
| New WD minimum | $4.50 |
| What the contractor now pays | $4.75 |
| **Allowable price adjustment** | **$0.40 per hour** |

The contractor raised pay by $0.65, but only $0.40 ($4.50 - $4.10) was needed
to comply with the new WD. The other $0.25 was voluntary and is not part of
the adjustment.

If you were already paying at or above the new WD rate, the allowable wage
increase is zero.

### Step 4: Add the fringe benefit increase

Paragraph (d) covers the actual increase in wages **and fringe benefits**.
Apply the same rule as in Step 3 to H&W: the allowable H&W increase per hour is
the lower of how much you actually raised the H&W you pay and how much you
needed to raise it to reach the new WD H&W rate. Multiply by hours. If you
already paid H&W above the new rate, the allowable H&W increase is zero.

### Step 5: Add the accompanying taxes and insurance

Paragraph (e) includes the increases in **Social Security and unemployment
taxes and workers' compensation insurance** that go with the wage increase.
Apply your actual rates to the wage increase:

- Social Security 6.2% and Medicare 1.45% (employer share);
- federal unemployment tax (FUTA), usually 0.6% net on the first $7,000 of
  each employee's wages per year, which may be 0 if your employees are already
  over that amount when the increase is paid;
- your state unemployment rate (SUTA), from your state rate notice;
- your workers' compensation rate, from your policy.

### Step 6: Leave out what the clause excludes

Paragraph (e) **excludes general and administrative costs, overhead and
profit**. Do not add them. The worksheet in this repository refuses input
that contains them.

### Step 7: Total it

Total for each occupation = allowable wage increase x hours + H&W increase x
hours + taxes and insurance. Add the occupations together.

## 4. The 30-day deadline and what the notice must contain

Paragraph (f) requires you to **notify the contracting officer of any increase
claimed within 30 days after receiving the new WD**, unless the contracting
officer extends that period in writing. Write down the date you received the
WD and count 30 days.

The notice must include:

- the **amount claimed**;
- for time-and-materials or labor-hour contracts, the change in the fixed
  hourly labor rates; and
- **supporting data**, including payroll records, that the contracting officer
  may reasonably require.

You must keep performing the contract while the adjustment is being reviewed.

`lcv price-adjustment` produces a generic draft notice
(`price_adjustment_notice_DRAFT.md`) with fields in square brackets to fill
in, and warns you if the 30-day period has already ended.

## 5. Records to keep for 3 years

Paragraph (g) gives the contracting officer or an authorized representative
access to directly pertinent books, documents, papers and records **until 3
years after final payment** under the contract. Keep together:

- the prior and new WDs;
- the date you received the new WD;
- payroll records before and after the change, by occupation;
- records of H&W payments;
- the hours basis you used;
- your tax and workers' compensation rate notices;
- the worksheet and the notice you sent.

## 6. Common mistakes

- **Missing the 30-day deadline.** Ask for a written extension before the
  period ends if you need more time.
- **Including profit, overhead or G&A.** Paragraph (e) excludes them.
- **Claiming the full WD increase when you already paid above the old WD.**
  Only the increase needed to reach the new WD from what you were paying is
  allowable, as the $0.40 example shows.
- **Claiming a voluntary raise.** Anything above what the new WD requires is
  not part of the adjustment. The same applies to H&W.
- **Not reporting a decrease.** Paragraph (f) requires prompt notice of
  decreases too.
- **Not having payroll records that prove the increase.** Paragraph (f) asks
  for payroll records; without them you cannot support the claim.

## 7. A complete example

This example uses the fictitious data in
`sample-data/price_adjustment_input.csv` and is the same as the output of
`lcv price-adjustment`. A fictitious contractor has a janitorial and security
contract. The new WD was received on 2026-09-15.

| Occupation | Prior WD | New WD | Paid before | Paid after | Allowable / hour | Hours |
|---|---:|---:|---:|---:|---:|---:|
| Janitor | 17.20 | 17.85 | 17.50 | 17.85 | 0.35 | 24,960 |
| Laborer, Grounds Maintenance | 18.05 | 18.60 | 18.05 | 18.60 | 0.55 | 2,080 |
| Guard I | 19.40 | 20.10 | 20.00 | 20.50 | 0.10 | 12,480 |

- **Janitor:** the contractor already paid $17.50, above the prior WD. Only
  $17.85 - $17.50 = $0.35 is allowable.
- **Laborer:** paid exactly the WD before and after: $0.55.
- **Guard I:** like the clause's own example. The contractor paid $20.00 and
  raised pay to $20.50, but only $20.10 - $20.00 = $0.10 was needed.

H&W rose from $5.55 to $5.92 between the two WDs, and the contractor paid
exactly those amounts, so $0.37 per hour is allowable. Taxes and insurance
are applied at 14.45% of the wage increase (6.2% + 1.45% + 0.6% + an example
SUTA rate of 2.7% + an example workers' compensation rate of 3.5%).

| Occupation | Wage increase | H&W increase | Taxes and insurance | Total |
|---|---:|---:|---:|---:|
| Janitor | 8,736.00 | 9,235.20 | 1,262.35 | 19,233.55 |
| Laborer, Grounds Maintenance | 1,144.00 | 769.60 | 165.31 | 2,078.91 |
| Guard I | 1,248.00 | 4,617.60 | 180.34 | 6,045.94 |
| **Total** | | | | **27,358.40** |

No overhead, G&A or profit is included. The notice was due by 2026-10-15
(2026-09-15 + 30 days).

## 8. Sources (accessed 2026-10-30)

- FAR 52.222-43, Fair Labor Standards Act and Service Contract Labor Standards - Price Adjustment (Multiple Year and Option Contracts) (Aug 2018): <https://www.acquisition.gov/far/52.222-43>
- FAR 22.1006, Solicitation provisions and contract clauses: <https://www.acquisition.gov/far/22.1006>
- FAR 52.222-41, Service Contract Labor Standards: <https://www.acquisition.gov/far/52.222-41>
- Wage determinations on sam.gov: <https://sam.gov/wage-determinations>
- DOL Wage and Hour Division, All Agency Memoranda (AAM 250, AAM 252): <https://sam.gov/content/wage-determinations/resources/all-agency-memos>
- U.S. Department of State, Acquisition Alert 26-14, FAR Class Deviation for FAR Part 22: <https://acquisition.gov/sites/default/files/page_file_uploads/DOS_RFO_Deviation_Part-22.pdf>
- FAR Overhaul (RFO), Part 22 model deviation text: <https://www.acquisition.gov/far-overhaul/far-part-deviation-guide/far-overhaul-part-22>
- IRS Topic no. 751, Social Security and Medicare withholding rates: <https://www.irs.gov/taxtopics/tc751>
- IRS Topic no. 759, Form 940 - Employer's Annual Federal Unemployment (FUTA) Tax Return: <https://www.irs.gov/taxtopics/tc759>

> **This guide is general information, not legal or accounting advice. Always read your contract and the current FAR text.**

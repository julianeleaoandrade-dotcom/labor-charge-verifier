"""Rule catalog.

Every check in this toolkit has an entry here. Each finding produced by the
checks carries the ``rule_id`` of the rule that produced it, so a reviewer can
always trace a finding back to what was checked, why, and on what basis.

The long-form explanation of every rule, with links to sources, is in
``docs/rules-catalog.md``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    rule_id: str
    module: str
    title: str
    checks: str
    basis: str
    severity: str  # "high", "medium" or "low"


SEVERITIES = ("high", "medium", "low")

# Values allowed in the "direction" field of a finding.
DIRECTIONS = (
    "overbilled",        # the invoice charges more than the records support
    "underbilled",       # the invoice charges less than the records support
    "underpaid_worker",  # the worker was paid less than required or recorded
    "overpaid_worker",   # the worker was paid more than recorded hours support
    "none",              # a control issue with no direct dollar direction
)

RULES: dict[str, Rule] = {
    # ------------------------------------------------------------------
    # Module 1 - Invoice vs. records
    # ------------------------------------------------------------------
    "INV-01": Rule(
        "INV-01", "invoice", "Billed employee is on the roster and active",
        "Each billed employee exists on the contract roster and was employed "
        "(between hire date and termination date) for every day of the billed "
        "service period.",
        "Charges must be supported by records of work actually performed "
        "(2 CFR 200.430(g)(1) for federal awards; contract payment terms).",
        "high",
    ),
    "INV-02": Rule(
        "INV-02", "invoice", "Billed hours match timesheets",
        "Hours billed on each invoice line equal the hours recorded on "
        "timesheets for the same employee, post and dates, within the "
        "configured tolerance.",
        "Charges must be based on records that accurately reflect the work "
        "performed (2 CFR 200.430(g)(1)).",
        "high",
    ),
    "INV-03": Rule(
        "INV-03", "invoice", "Hours paid on payroll match timesheets",
        "For each employee and workweek, regular plus overtime hours on the "
        "payroll equal the hours recorded on timesheets, within the "
        "configured tolerance.",
        "Payroll is the record that proves the labor cost behind a charge; it "
        "must agree with timekeeping (2 CFR 200.430(g)(1); 29 CFR 4.6(g)).",
        "medium",
    ),
    "INV-04": Rule(
        "INV-04", "invoice", "Unit price is the contract price in effect on the service date",
        "The unit price on each invoice line equals the contract price for "
        "that post on the service dates. Lines that cross a price change are "
        "flagged so they can be split.",
        "Contract pricing terms; a stale price produces an error in either "
        "direction.",
        "high",
    ),
    "INV-05": Rule(
        "INV-05", "invoice", "Billed headcount per post matches the contract",
        "The number of distinct employees billed to a post for a service "
        "period does not exceed the headcount the contract authorizes. "
        "Billing fewer people than authorized is reported as a staffing "
        "item for review.",
        "Contract staffing terms.",
        "medium",
    ),
    "INV-06": Rule(
        "INV-06", "invoice", "No duplicate lines and no employee on two posts at once",
        "No invoice line is repeated, and no employee is billed to two posts "
        "for overlapping dates.",
        "A person cannot perform two full posts at the same time; duplicate "
        "lines are charges with no separate work behind them.",
        "high",
    ),
    "INV-07": Rule(
        "INV-07", "invoice", "Service dates are valid",
        "Each line has a start date on or before its end date (no negative "
        "day counts) and falls inside the invoice period.",
        "Date errors make the charge impossible to verify.",
        "high",
    ),
    "INV-08": Rule(
        "INV-08", "invoice", "Line amounts and invoice total recalculate",
        "Each line amount equals hours times unit price, and the stated "
        "invoice total equals the sum of the stated line amounts.",
        "Arithmetic accuracy of the claim for payment.",
        "medium",
    ),
    # ------------------------------------------------------------------
    # Module 2 - Wage-determination compliance
    # ------------------------------------------------------------------
    "WAGE-01": Rule(
        "WAGE-01", "wages", "Hourly rate paid is at least the wage determination rate",
        "The hourly rate paid to each employee is at least the rate in the "
        "wage determination (WD) for the employee's occupation in the "
        "contract's WD.",
        "41 U.S.C. 6703; 29 CFR 4.6; FAR 52.222-41.",
        "high",
    ),
    "WAGE-02": Rule(
        "WAGE-02", "wages", "Health and welfare (H&W) benefit is at least the required amount",
        "The H&W amount paid (in cash or as plan contributions) for each "
        "workweek is at least the configured H&W rate times the hours paid, "
        "up to 40 hours per week.",
        "29 CFR 4.175(a); DOL WHD All Agency Memoranda 250 and 252.",
        "high",
    ),
    "WAGE-03": Rule(
        "WAGE-03", "wages", "Overtime over 40 hours per week is paid at 1.5 times the rate",
        "For each workweek, hours over 40 are paid at no less than 1.5 times "
        "the hourly rate paid. This is the basic Fair Labor Standards Act "
        "rule only; special cases are out of scope.",
        "29 U.S.C. 207(a)(1).",
        "high",
    ),
    "WAGE-04": Rule(
        "WAGE-04", "wages", "Employee's occupation is listed on the wage determination",
        "Each employee's occupation is listed on the contract's WD. If it is "
        "not, the finding says a conformance request may be needed. The tool "
        "does not calculate a conformed rate.",
        "29 CFR 4.6(b)(2); FAR 52.222-41(c)(2).",
        "medium",
    ),
    # ------------------------------------------------------------------
    # Module 3 - FAR 52.222-43 price adjustment worksheet
    # ------------------------------------------------------------------
    "PA-01": Rule(
        "PA-01", "price_adjustment", "Allowable wage increase per occupation",
        "Allowable increase = the lower of (a) the actual increase in the "
        "rate paid and (b) the increase needed to bring the rate previously "
        "paid up to the new WD rate. Never below zero.",
        "FAR 52.222-43(d), including the clause's own numeric example.",
        "high",
    ),
    "PA-02": Rule(
        "PA-02", "price_adjustment", "Health and welfare increase",
        "Adds the difference between the H&W rate on the new WD and on the "
        "prior WD, per hour.",
        "FAR 52.222-43(d) (wages and fringe benefits).",
        "medium",
    ),
    "PA-03": Rule(
        "PA-03", "price_adjustment", "Accompanying payroll taxes and insurance",
        "Adds the increase in Social Security, Medicare, unemployment taxes "
        "and workers' compensation insurance that follows from the wage "
        "increase, using rates from the configuration file.",
        "FAR 52.222-43(e).",
        "medium",
    ),
    "PA-04": Rule(
        "PA-04", "price_adjustment", "No overhead, G&A or profit",
        "Refuses input that contains overhead, general and administrative "
        "(G&A), profit, fee or markup amounts.",
        "FAR 52.222-43(e) excludes these from the adjustment.",
        "high",
    ),
    "PA-05": Rule(
        "PA-05", "price_adjustment", "30-day notice deadline",
        "Deadline = date the new WD was received + 30 days. Warns when the "
        "deadline has passed.",
        "FAR 52.222-43(f).",
        "high",
    ),
}


def get_rule(rule_id: str) -> Rule:
    return RULES[rule_id]

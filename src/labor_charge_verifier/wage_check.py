"""Module 2 - Wage-determination compliance.

Checks each payroll record against the wage determination (WD) that applies
to the contract. The same records that stop an hour billed in excess also
show when a worker was paid less than required; every underpayment is
reported with the amount owed to the worker.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .common import Finding, InputError, cfg, read_csv, require_unique, to_float
from .invoice_check import load_contract, load_payroll, load_roster

WD_COLUMNS = ["wd_number", "revision", "state", "area", "occupation_code",
              "occupation_title", "hourly_rate"]


@dataclass
class WageData:
    contract: pd.DataFrame
    roster: pd.DataFrame
    payroll: pd.DataFrame
    wage_determination: pd.DataFrame


def find_wd_file(data_dir: Path) -> Path:
    candidates = sorted(data_dir.glob("wage_determination*.csv"))
    if not candidates:
        raise InputError(f"No wage_determination*.csv file found in {data_dir}")
    if len(candidates) > 1:
        names = ", ".join(c.name for c in candidates)
        raise InputError(f"More than one wage determination file found: {names}")
    return candidates[0]


def load_wage_data(data_dir: str | Path) -> WageData:
    data_dir = Path(data_dir)
    contract = load_contract(data_dir)
    roster = load_roster(data_dir)
    payroll = load_payroll(data_dir)
    wd_path = find_wd_file(data_dir)
    wd = read_csv(wd_path, WD_COLUMNS, comment="#")
    wd = to_float(wd, ["hourly_rate"], wd_path.name)
    for number, group in wd.groupby("wd_number"):
        if group["revision"].nunique() > 1:
            raise InputError(f"{wd_path.name}: WD {number} has more than one revision "
                             f"({sorted(group['revision'].unique())}). Keep only the "
                             "revision incorporated in the contract.")
    require_unique(wd, ["wd_number", "occupation_code"], wd_path.name)
    return WageData(contract, roster, payroll, wd)


def check_wages(data: WageData, config: dict) -> list[Finding]:
    money_tol = float(cfg(config, "tolerances", "money"))
    hw_rate = float(cfg(config, "health_and_welfare", "rate_per_hour"))
    hw_cap = float(cfg(config, "health_and_welfare", "weekly_hour_cap"))
    hw_basis = cfg(config, "health_and_welfare", "basis")
    ot_threshold = float(cfg(config, "overtime", "weekly_threshold_hours"))
    ot_multiplier = float(cfg(config, "overtime", "multiplier"))
    if hw_basis not in ("hours_paid", "hours_worked"):
        raise InputError("health_and_welfare.basis must be 'hours_paid' or 'hours_worked'")

    wd_numbers = sorted(set(data.contract["wd_number"]))
    if len(wd_numbers) != 1:
        raise InputError(f"contract.csv must reference exactly one wd_number; found {wd_numbers}")
    wd = data.wage_determination[data.wage_determination["wd_number"] == wd_numbers[0]]
    if wd.empty:
        raise InputError(f"The wage determination file has no rows for WD {wd_numbers[0]}")
    wd_rates = dict(zip(wd["occupation_code"], wd["hourly_rate"]))
    roster = data.roster.set_index("employee_id")

    findings: list[Finding] = []
    flagged_occupation: set[str] = set()

    for _, row in data.payroll.iterrows():
        employee = row["employee_id"]
        period = f"{row['week_start']} to {row['week_end']}"
        if employee not in roster.index:
            findings.append(Finding(
                "WAGE-04", "Payroll employee is not on the contract roster, so the "
                "occupation and WD rate cannot be determined.",
                employee, period=period))
            continue
        person = roster.loc[employee]
        occupation = person["occupation_code"]
        rate = row["hourly_rate_paid"]
        regular, overtime = row["regular_hours"], row["overtime_hours"]
        leave = row["paid_leave_hours"]

        # WAGE-04: occupation listed on the WD.
        if occupation not in wd_rates:
            if employee not in flagged_occupation:
                findings.append(Finding(
                    "WAGE-04",
                    f"Occupation '{person['occupation_title']}' ({occupation}) is not "
                    f"listed on WD {wd_numbers[0]}. A conformance request may be needed "
                    "under the contract's labor standards clause. The tool does not "
                    "calculate a conformed rate; WAGE-01 is not applied to this employee.",
                    employee, person["post_id"], period="all weeks"))
                flagged_occupation.add(employee)
        else:
            # WAGE-01: rate paid >= WD rate (straight time and overtime hours).
            wd_rate = wd_rates[occupation]
            if rate + money_tol < wd_rate:
                shortfall = wd_rate - rate
                owed = shortfall * (regular + leave) + shortfall * ot_multiplier * overtime
                findings.append(Finding(
                    "WAGE-01",
                    f"Paid {rate:,.2f}/hour; WD rate for {person['occupation_title']} "
                    f"is {wd_rate:,.2f}/hour. Shortfall {shortfall:,.2f}/hour on "
                    f"{regular + leave:g} straight-time and {overtime:g} overtime hours.",
                    employee, person["post_id"], period=period,
                    billed_amount=rate, expected_amount=wd_rate,
                    difference=rate - wd_rate, direction="underpaid_worker",
                    amount_owed_to_worker=owed))

        # WAGE-02: H&W paid >= rate x hours, capped per week.
        basis_hours = regular + overtime + (leave if hw_basis == "hours_paid" else 0.0)
        hw_hours = min(basis_hours, hw_cap)
        hw_required = hw_rate * hw_hours
        if row["hw_paid"] + money_tol < hw_required:
            owed = hw_required - row["hw_paid"]
            findings.append(Finding(
                "WAGE-02",
                f"H&W paid {row['hw_paid']:,.2f}; required {hw_rate:,.2f} x "
                f"{hw_hours:g} hours = {hw_required:,.2f}.",
                employee, person["post_id"], period=period,
                billed_amount=row["hw_paid"], expected_amount=hw_required,
                difference=row["hw_paid"] - hw_required, direction="underpaid_worker",
                amount_owed_to_worker=owed))

        # WAGE-03: hours over the weekly threshold paid at 1.5x.
        total_hours = regular + overtime
        required_ot_hours = max(0.0, total_hours - ot_threshold)
        required_pay = (min(total_hours, ot_threshold) * rate
                        + required_ot_hours * ot_multiplier * rate)
        actual_pay = regular * rate + overtime * row["overtime_rate_paid"]
        if actual_pay + money_tol < required_pay:
            owed = required_pay - actual_pay
            findings.append(Finding(
                "WAGE-03",
                f"{total_hours:g} hours worked in the week; {required_ot_hours:g} hours "
                f"are over {ot_threshold:g} and must be paid at {ot_multiplier:g} x "
                f"{rate:,.2f}. Payroll shows {regular:g} regular and {overtime:g} "
                f"overtime hours (overtime rate {row['overtime_rate_paid']:,.2f}).",
                employee, person["post_id"], period=period,
                billed_amount=actual_pay, expected_amount=required_pay,
                difference=actual_pay - required_pay, direction="underpaid_worker",
                amount_owed_to_worker=owed))

    return findings

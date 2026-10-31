"""Module 1 - Invoice vs. records.

Checks each line of a monthly labor invoice against the contract roster,
timesheets, payroll and contract unit prices. Errors are reported in both
directions: charges the records do not support (overbilled) and work the
records support but the invoice left out (underbilled).

Dollar amounts are attributed so that the same dollar is not counted by two
rules:

- A line that fails INV-01 (employee not active), INV-06 (duplicate or
  same-post overlap) or INV-07 (invalid dates) is not checked again by INV-02
  and INV-04.
- INV-02 values the hours difference at the billed unit price; INV-04 values
  the price difference on the hours the timesheets support. Together they add
  up to billed amount minus supported amount.
- INV-08 reports arithmetic errors in the stated line amount separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .common import (Finding, InputError, cfg, plural, read_csv, require_unique,
                     to_float, week_start_index, WEEKDAYS)

CONTRACT_COLUMNS = ["contract_id", "contractor_name", "wd_number", "post_id",
                    "post_name", "occupation_code", "required_headcount",
                    "billing_unit", "unit_price", "price_effective_start",
                    "price_effective_end"]
ROSTER_COLUMNS = ["contract_id", "employee_id", "first_name", "last_name",
                  "occupation_code", "occupation_title", "post_id",
                  "hire_date", "termination_date"]
TIMESHEET_COLUMNS = ["employee_id", "post_id", "work_date", "hours"]
PAYROLL_COLUMNS = ["employee_id", "week_start", "week_end", "regular_hours",
                   "overtime_hours", "paid_leave_hours", "hourly_rate_paid",
                   "overtime_rate_paid", "hw_paid"]
PAYROLL_NUMERIC = ["regular_hours", "overtime_hours", "paid_leave_hours",
                   "hourly_rate_paid", "overtime_rate_paid", "hw_paid"]
INVOICE_COLUMNS = ["invoice_number", "invoice_period_start", "invoice_period_end",
                   "line_type", "line_id", "employee_id", "post_id",
                   "service_start", "service_end", "hours_billed", "unit_price",
                   "line_amount"]


@dataclass
class InvoiceData:
    contract: pd.DataFrame
    roster: pd.DataFrame
    timesheets: pd.DataFrame
    payroll: pd.DataFrame
    invoice: pd.DataFrame


def load_contract(data_dir: Path) -> pd.DataFrame:
    contract = read_csv(data_dir / "contract.csv", CONTRACT_COLUMNS,
                        ["price_effective_start", "price_effective_end"])
    contract = to_float(contract, ["unit_price", "required_headcount"], "contract.csv")
    for column in ("price_effective_start", "price_effective_end"):
        if contract[column].isna().any():
            raise InputError(f"contract.csv: blank value in required column '{column}'.")
    return contract


def load_roster(data_dir: Path) -> pd.DataFrame:
    roster = read_csv(data_dir / "roster.csv", ROSTER_COLUMNS, ["hire_date", "termination_date"])
    require_unique(roster, ["employee_id"], "roster.csv")
    return roster


def load_payroll(data_dir: Path) -> pd.DataFrame:
    payroll = read_csv(data_dir / "payroll.csv", PAYROLL_COLUMNS, ["week_start", "week_end"])
    payroll = to_float(payroll, PAYROLL_NUMERIC, "payroll.csv")
    if payroll["week_start"].isna().any() or payroll["week_end"].isna().any():
        raise InputError("payroll.csv: week_start and week_end are required on every row.")
    require_unique(payroll, ["employee_id", "week_start"], "payroll.csv")
    return payroll


def load_invoice_data(data_dir: str | Path) -> InvoiceData:
    data_dir = Path(data_dir)
    contract = load_contract(data_dir)
    roster = load_roster(data_dir)
    timesheets = read_csv(data_dir / "timesheets.csv", TIMESHEET_COLUMNS, ["work_date"])
    timesheets = to_float(timesheets, ["hours"], "timesheets.csv")
    if timesheets["work_date"].isna().any():
        raise InputError("timesheets.csv: work_date is required on every row.")
    payroll = load_payroll(data_dir)
    invoice = read_csv(data_dir / "invoice.csv", INVOICE_COLUMNS,
                       ["invoice_period_start", "invoice_period_end",
                        "service_start", "service_end"])
    invoice["line_type"] = invoice["line_type"].str.upper()
    bad_types = set(invoice["line_type"]) - {"LINE", "TOTAL"}
    if bad_types:
        raise InputError(f"invoice.csv: unknown line_type values {sorted(bad_types)}")
    is_line = invoice["line_type"] == "LINE"
    invoice = to_float(invoice, ["hours_billed", "unit_price"], "invoice.csv", rows=is_line)
    invoice = to_float(invoice, ["line_amount"], "invoice.csv")
    require_unique(invoice[is_line], ["line_id"], "invoice.csv")
    return InvoiceData(contract, roster, timesheets, payroll, invoice)


def _period(start: date | None, end: date | None) -> str:
    return f"{start or '(missing)'} to {end or '(missing)'}"


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def _direction(billed: float, expected: float) -> str:
    return "overbilled" if billed > expected else "underbilled"


def _ts_hours(timesheets: pd.DataFrame, employee: str, post: str | None,
              start: date, end: date) -> float:
    mask = ((timesheets["employee_id"] == employee)
            & (timesheets["work_date"] >= start) & (timesheets["work_date"] <= end))
    if post is not None:
        mask &= timesheets["post_id"] == post
    return float(timesheets.loc[mask, "hours"].sum())


def check_invoice(data: InvoiceData, config: dict) -> list[Finding]:
    hours_tol = float(cfg(config, "tolerances", "hours"))
    money_tol = float(cfg(config, "tolerances", "money"))
    week_start = week_start_index(config)
    findings: list[Finding] = []

    lines = data.invoice[data.invoice["line_type"] == "LINE"].copy()
    totals = data.invoice[data.invoice["line_type"] == "TOTAL"]
    roster = data.roster.set_index("employee_id")
    timesheets = data.timesheets

    # Lines later checks should skip (line_id -> rule that excluded it).
    skip: dict[str, str] = {}
    # Lines that should not count toward headcount.
    not_headcount: set[str] = set()

    # --- INV-07: valid dates -------------------------------------------
    for _, row in lines.iterrows():
        start, end = row["service_start"], row["service_end"]
        if start is None or end is None:
            findings.append(Finding(
                "INV-07", "Service start or end date is missing.",
                row["employee_id"], row["post_id"], row["line_id"],
                _period(start, end), billed_amount=row["line_amount"]))
            skip[row["line_id"]] = "INV-07"
            not_headcount.add(row["line_id"])
            continue
        if end < start:
            day_count = (end - start).days + 1
            findings.append(Finding(
                "INV-07",
                f"Service end date is before the start date, giving a day count of "
                f"{day_count}. The charge cannot be verified until the dates are "
                "corrected.",
                row["employee_id"], row["post_id"], row["line_id"],
                _period(start, end), billed_amount=row["line_amount"]))
            skip[row["line_id"]] = "INV-07"
            continue
        p_start, p_end = row["invoice_period_start"], row["invoice_period_end"]
        if p_start and p_end and (start < p_start or end > p_end):
            findings.append(Finding(
                "INV-07",
                f"Service dates fall outside the invoice period {p_start} to {p_end}.",
                row["employee_id"], row["post_id"], row["line_id"],
                _period(start, end), billed_amount=row["line_amount"]))

    # --- INV-06: exact duplicate lines ---------------------------------
    dup_key = ["employee_id", "post_id", "service_start", "service_end",
               "hours_billed", "unit_price", "line_amount"]
    duplicated = lines.duplicated(subset=dup_key, keep="first")
    for _, row in lines[duplicated].iterrows():
        original = lines[(lines[dup_key] == row[dup_key]).all(axis=1)].iloc[0]
        findings.append(Finding(
            "INV-06",
            f"Line repeats line {original['line_id']} exactly. The repeated line "
            "has no separate work behind it.",
            row["employee_id"], row["post_id"], row["line_id"],
            _period(row["service_start"], row["service_end"]),
            billed_amount=row["line_amount"], expected_amount=0.0,
            difference=row["line_amount"], direction="overbilled"))
        skip.setdefault(row["line_id"], "INV-06")
        not_headcount.add(row["line_id"])

    # --- INV-01: employee on roster and active -------------------------
    for _, row in lines.iterrows():
        line_id = row["line_id"]
        if line_id in skip:
            continue
        employee = row["employee_id"]
        start, end = row["service_start"], row["service_end"]
        amount = row["hours_billed"] * row["unit_price"]
        if employee not in roster.index:
            findings.append(Finding(
                "INV-01", "Billed employee is not on the contract roster.",
                employee, row["post_id"], line_id, _period(start, end),
                billed_amount=amount, expected_amount=0.0, difference=amount,
                direction="overbilled"))
            skip[line_id] = "INV-01"
            not_headcount.add(line_id)
            continue
        person = roster.loc[employee]
        hire, term = person["hire_date"], person["termination_date"]
        active_start = max(start, hire) if hire else start
        active_end = min(end, term) if term else end
        if active_start == start and active_end == end:
            continue
        if active_end < active_start:
            expected_hours = 0.0
            detail = "for any day of the billed period"
        else:
            expected_hours = _ts_hours(timesheets, employee, row["post_id"],
                                       active_start, active_end)
            detail = f"for part of the billed period (active {active_start} to {active_end})"
        expected = expected_hours * row["unit_price"]
        findings.append(Finding(
            "INV-01",
            f"Employee was not employed {detail}. Hire date: {hire or '(none)'}; "
            f"termination date: {term or '(none)'}.",
            employee, row["post_id"], line_id, _period(start, end),
            billed_amount=amount, expected_amount=expected,
            difference=amount - expected, direction=_direction(amount, expected)))
        skip[line_id] = "INV-01"
        if expected_hours == 0:
            not_headcount.add(line_id)

    # --- INV-06: same employee on overlapping lines --------------------
    candidates = lines[~lines["line_id"].isin(skip.keys())]
    for employee, group in candidates.groupby("employee_id"):
        records = group.sort_values(["service_start", "line_id"]).to_dict("records")
        for i, first in enumerate(records):
            for second in records[i + 1:]:
                if second["line_id"] in skip or first["line_id"] in skip:
                    continue
                overlap_start = max(first["service_start"], second["service_start"])
                overlap_end = min(first["service_end"], second["service_end"])
                if overlap_start > overlap_end:
                    continue
                period = _period(overlap_start, overlap_end)
                if first["post_id"] == second["post_id"]:
                    # Same post: the timesheet hours can support only one line.
                    amount = second["hours_billed"] * second["unit_price"]
                    findings.append(Finding(
                        "INV-06",
                        f"Line overlaps line {first['line_id']} for the same employee "
                        f"and post ({overlap_start} to {overlap_end}). The hours on the "
                        "timesheets are already billed on the earlier line.",
                        employee, second["post_id"], second["line_id"], period,
                        billed_amount=amount, expected_amount=0.0, difference=amount,
                        direction="overbilled"))
                    skip[second["line_id"]] = "INV-06"
                    not_headcount.add(second["line_id"])
                else:
                    findings.append(Finding(
                        "INV-06",
                        f"Employee is billed on line {first['line_id']} (post "
                        f"{first['post_id']}) and line {second['line_id']} (post "
                        f"{second['post_id']}) for overlapping dates "
                        f"{overlap_start} to {overlap_end}. See INV-02 for the "
                        "amount the timesheets do not support.",
                        employee, second["post_id"], second["line_id"], period,
                        direction="none"))

    active_lines = lines[~lines["line_id"].isin(skip.keys())]

    # --- INV-02: billed hours vs timesheets ----------------------------
    supported_hours: dict[str, float] = {}
    for _, row in active_lines.iterrows():
        ts_hours = _ts_hours(timesheets, row["employee_id"], row["post_id"],
                             row["service_start"], row["service_end"])
        supported_hours[row["line_id"]] = ts_hours
        if abs(row["hours_billed"] - ts_hours) > hours_tol:
            billed = row["hours_billed"] * row["unit_price"]
            expected = ts_hours * row["unit_price"]
            findings.append(Finding(
                "INV-02",
                f"Billed {row['hours_billed']:g} hours; timesheets show "
                f"{ts_hours:g} hours for this employee, post and period.",
                row["employee_id"], row["post_id"], row["line_id"],
                _period(row["service_start"], row["service_end"]),
                billed_amount=billed, expected_amount=expected,
                difference=billed - expected, direction=_direction(billed, expected)))
        else:
            supported_hours[row["line_id"]] = row["hours_billed"]

    # --- INV-04: unit price in effect on the service date --------------
    findings.extend(_check_prices(active_lines, data.contract, timesheets,
                                  supported_hours, money_tol))

    # --- INV-08: line arithmetic and invoice total ---------------------
    for _, row in lines.iterrows():
        if skip.get(row["line_id"]) == "INV-06":
            continue
        recalculated = row["hours_billed"] * row["unit_price"]
        if abs(row["line_amount"] - recalculated) > money_tol:
            findings.append(Finding(
                "INV-08",
                f"Line amount {row['line_amount']:,.2f} does not equal "
                f"{row['hours_billed']:g} hours x {row['unit_price']:,.2f} = "
                f"{recalculated:,.2f}.",
                row["employee_id"], row["post_id"], row["line_id"],
                _period(row["service_start"], row["service_end"]),
                billed_amount=row["line_amount"], expected_amount=recalculated,
                difference=row["line_amount"] - recalculated,
                direction=_direction(row["line_amount"], recalculated)))
    lines_sum = float(lines["line_amount"].sum()) if not lines.empty else 0.0
    if totals.empty:
        findings.append(Finding(
            "INV-08", "Invoice has no TOTAL row, so the stated total cannot be checked.",
            severity="low"))
    for _, row in totals.iterrows():
        if abs(row["line_amount"] - lines_sum) > money_tol:
            findings.append(Finding(
                "INV-08",
                f"Stated invoice total {row['line_amount']:,.2f} does not equal the "
                f"sum of the stated line amounts {lines_sum:,.2f}.",
                line_id=row["line_id"],
                period=_period(row["invoice_period_start"], row["invoice_period_end"]),
                billed_amount=row["line_amount"], expected_amount=lines_sum,
                difference=row["line_amount"] - lines_sum,
                direction=_direction(row["line_amount"], lines_sum)))

    # --- INV-05: headcount per post ------------------------------------
    findings.extend(_check_headcount(lines, not_headcount, data.contract))

    # --- INV-03: payroll hours vs timesheets ---------------------------
    findings.extend(_check_payroll_hours(data.payroll, timesheets, hours_tol, week_start))

    return findings


def _price_on(contract: pd.DataFrame, post_id: str, day: date) -> float | None:
    rows = contract[(contract["post_id"] == post_id)
                    & (contract["price_effective_start"] <= day)
                    & (contract["price_effective_end"] >= day)]
    if rows.empty:
        return None
    return float(rows.iloc[0]["unit_price"])


def _check_prices(lines: pd.DataFrame, contract: pd.DataFrame, timesheets: pd.DataFrame,
                  supported_hours: dict[str, float], money_tol: float) -> list[Finding]:
    findings = []
    posts = set(contract["post_id"])
    for _, row in lines.iterrows():
        start, end = row["service_start"], row["service_end"]
        period = _period(start, end)
        if row["post_id"] not in posts:
            findings.append(Finding(
                "INV-04", f"Post {row['post_id']} is not in the contract price list.",
                row["employee_id"], row["post_id"], row["line_id"], period,
                billed_amount=row["hours_billed"] * row["unit_price"]))
            continue
        prices = {day: _price_on(contract, row["post_id"], day) for day in _days(start, end)}
        if any(p is None for p in prices.values()):
            findings.append(Finding(
                "INV-04", "No contract price is in effect for one or more service dates.",
                row["employee_id"], row["post_id"], row["line_id"], period,
                billed_amount=row["hours_billed"] * row["unit_price"]))
            continue
        distinct = sorted(set(prices.values()))
        if len(distinct) == 1:
            contract_price = distinct[0]
            note = f"contract price in effect for these dates is {contract_price:,.2f}"
        else:
            # Weight each day's price by the hours worked that day.
            mask = ((timesheets["employee_id"] == row["employee_id"])
                    & (timesheets["post_id"] == row["post_id"])
                    & (timesheets["work_date"] >= start)
                    & (timesheets["work_date"] <= end))
            worked = timesheets[mask]
            if worked["hours"].sum() > 0:
                contract_price = float(sum(h * prices[d] for d, h in
                                           zip(worked["work_date"], worked["hours"]))
                                       / worked["hours"].sum())
            else:
                contract_price = sum(prices.values()) / len(prices)
            note = ("line crosses a contract price change; split the line at the "
                    f"change date (hour-weighted contract price {contract_price:,.4f})")
            findings.append(Finding(
                "INV-04", f"The {note}.", row["employee_id"], row["post_id"],
                row["line_id"], period, severity="medium"))
        if abs(row["unit_price"] - contract_price) > money_tol:
            hours = supported_hours.get(row["line_id"], row["hours_billed"])
            billed = hours * row["unit_price"]
            expected = hours * contract_price
            findings.append(Finding(
                "INV-04",
                f"Billed unit price {row['unit_price']:,.2f}; {note}. Difference "
                f"valued on {hours:g} hours supported by timesheets.",
                row["employee_id"], row["post_id"], row["line_id"], period,
                billed_amount=billed, expected_amount=expected,
                difference=billed - expected, direction=_direction(billed, expected)))
    return findings


def _check_headcount(lines: pd.DataFrame, excluded: set[str],
                     contract: pd.DataFrame) -> list[Finding]:
    """Count distinct billed employees per post for each day and compare with
    the headcount the contract requires on that day. Consecutive days with the
    same result are reported as one finding."""
    findings = []
    eligible = lines[~lines["line_id"].isin(excluded)]
    eligible = eligible[eligible["service_start"].notna() & eligible["service_end"].notna()]
    if eligible.empty:
        return findings
    for post_id, group in eligible.groupby("post_id"):
        daily: dict[date, set[str]] = {}
        for _, row in group.iterrows():
            # Use the dates in order so a reversed-date typo does not distort headcount.
            first, last = sorted((row["service_start"], row["service_end"]))
            for day in _days(first, last):
                daily.setdefault(day, set()).add(row["employee_id"])
        runs: list[list] = []  # [start, end, billed, required]
        for day in sorted(daily):
            rows = contract[(contract["post_id"] == post_id)
                            & (contract["price_effective_start"] <= day)
                            & (contract["price_effective_end"] >= day)]
            if rows.empty:
                continue
            required = int(rows.iloc[0]["required_headcount"])
            billed = len(daily[day])
            if billed == required:
                continue
            if runs and runs[-1][1] == day - timedelta(days=1) and runs[-1][2:] == [billed, required]:
                runs[-1][1] = day
            else:
                runs.append([day, day, billed, required])
        for start, end, billed, required in runs:
            if billed > required:
                findings.append(Finding(
                    "INV-05",
                    f"{plural(billed, 'employee')} billed to post {post_id} on each day "
                    f"of this period; the contract authorizes {required}. Confirm that "
                    "the extra position was authorized in writing.",
                    post_id=post_id, period=_period(start, end), direction="overbilled"))
            else:
                findings.append(Finding(
                    "INV-05",
                    f"{plural(billed, 'employee')} billed to post {post_id} on each day "
                    f"of this period; the contract requires {required}. Confirm whether "
                    "the post was vacant.",
                    post_id=post_id, period=_period(start, end), severity="low"))
    return findings


def _week_of(day: date, start_index: int) -> date:
    return day - timedelta(days=(day.weekday() - start_index) % 7)


def _check_payroll_hours(payroll: pd.DataFrame, timesheets: pd.DataFrame,
                         hours_tol: float, start_index: int) -> list[Finding]:
    findings = []
    bad_weeks = payroll[payroll["week_start"].map(lambda d: d.weekday() != start_index)]
    if not bad_weeks.empty:
        raise InputError(
            f"payroll.csv: week_start must fall on {WEEKDAYS[start_index]} "
            f"(workweek.start_day); first mismatch: {bad_weeks.iloc[0]['week_start']}")
    seen: set[tuple[str, date]] = set()
    for _, row in payroll.iterrows():
        employee, w_start, w_end = row["employee_id"], row["week_start"], row["week_end"]
        seen.add((employee, w_start))
        ts_hours = _ts_hours(timesheets, employee, None, w_start, w_end)
        paid_hours = row["regular_hours"] + row["overtime_hours"]
        gap = ts_hours - paid_hours
        if abs(gap) <= hours_tol:
            continue
        if gap > 0:
            owed = gap * row["hourly_rate_paid"]
            findings.append(Finding(
                "INV-03",
                f"Payroll pays {paid_hours:g} hours; timesheets show {ts_hours:g} hours. "
                f"The worker may be owed {gap:g} hours (valued at the straight-time "
                "rate paid; overtime premium, if any, is not included).",
                employee, period=_period(w_start, w_end),
                expected_amount=ts_hours * row["hourly_rate_paid"],
                billed_amount=paid_hours * row["hourly_rate_paid"],
                difference=-owed, direction="underpaid_worker",
                amount_owed_to_worker=owed))
        else:
            findings.append(Finding(
                "INV-03",
                f"Payroll pays {paid_hours:g} hours; timesheets show only {ts_hours:g} "
                "hours. Confirm the extra paid hours before billing them.",
                employee, period=_period(w_start, w_end),
                billed_amount=paid_hours * row["hourly_rate_paid"],
                expected_amount=ts_hours * row["hourly_rate_paid"],
                difference=-gap * row["hourly_rate_paid"], direction="overpaid_worker"))
    # Timesheet weeks with no payroll record at all.
    if timesheets.empty:
        return findings
    weekly = timesheets.assign(week=timesheets["work_date"].map(lambda d: _week_of(d, start_index)))
    for (employee, w_start), group in weekly.groupby(["employee_id", "week"]):
        hours = float(group["hours"].sum())
        if hours > 0 and (employee, w_start) not in seen:
            findings.append(Finding(
                "INV-03",
                f"Timesheets show {hours:g} hours but there is no payroll record "
                "for this employee and week.",
                employee, period=_period(w_start, w_start + timedelta(days=6)),
                direction="underpaid_worker"))
    return findings

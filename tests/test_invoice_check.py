from datetime import date, timedelta

import pandas as pd
import pytest

from labor_charge_verifier.invoice_check import InvoiceData, check_invoice, load_invoice_data

D = date.fromisoformat


def keys(findings):
    return sorted((f.rule_id, f.employee_id, f.post_id, f.line_id) for f in findings)


# --------------------------------------------------------------------------
# The sample data: every planted error is found, and nothing else.
# This list must match sample-data/EXPECTED_FINDINGS.md.
# --------------------------------------------------------------------------
EXPECTED_SAMPLE = sorted([
    ("INV-01", "E017", "P01", "L036"),
    ("INV-01", "E099", "P03", "L041"),
    ("INV-02", "E003", "P01", "L005"),
    ("INV-02", "E010", "P02", "L021"),
    ("INV-02", "E011", "P03", "L023"),
    ("INV-03", "E007", "", ""),
    ("INV-04", "E005", "P01", "L010"),
    ("INV-05", "", "P01", ""),
    ("INV-05", "", "P03", ""),
    ("INV-06", "E008", "P02", "L016"),
    ("INV-06", "E011", "P03", "L023"),
    ("INV-07", "E013", "P03", "L028"),
    ("INV-08", "", "", "TOTAL"),
    ("INV-08", "E006", "P01", "L011"),
])


def test_sample_data_produces_exactly_the_expected_findings(sample_dir, config):
    findings = check_invoice(load_invoice_data(sample_dir), config)
    assert keys(findings) == EXPECTED_SAMPLE


def test_sample_data_reports_errors_in_both_directions(sample_dir, config):
    findings = check_invoice(load_invoice_data(sample_dir), config)
    over = round(sum(f.difference for f in findings if f.direction == "overbilled"
                     and f.difference is not None), 2)
    under = round(sum(-f.difference for f in findings if f.direction == "underbilled"), 2)
    owed = round(sum(f.amount_owed_to_worker or 0 for f in findings), 2)
    assert over == 10941.20
    assert under == 1303.20
    assert owed == 70.00


# --------------------------------------------------------------------------
# Small hand-built cases for individual rules
# --------------------------------------------------------------------------
def make_data(invoice_rows, timesheet_rows=None, roster_rows=None, payroll_rows=None,
              headcount=1):
    contract = pd.DataFrame([
        {"contract_id": "C1", "contractor_name": "Test Co", "wd_number": "WD1",
         "post_id": "P1", "post_name": "Post", "occupation_code": "11150",
         "required_headcount": float(headcount), "billing_unit": "hour",
         "unit_price": 10.0, "price_effective_start": D("2026-01-01"),
         "price_effective_end": D("2026-01-15")},
        {"contract_id": "C1", "contractor_name": "Test Co", "wd_number": "WD1",
         "post_id": "P1", "post_name": "Post", "occupation_code": "11150",
         "required_headcount": float(headcount), "billing_unit": "hour",
         "unit_price": 12.0, "price_effective_start": D("2026-01-16"),
         "price_effective_end": D("2026-12-31")},
    ])
    roster = pd.DataFrame(roster_rows or [
        {"contract_id": "C1", "employee_id": "A", "first_name": "x", "last_name": "y",
         "occupation_code": "11150", "occupation_title": "Janitor", "post_id": "P1",
         "hire_date": D("2025-01-01"), "termination_date": None},
    ])
    timesheets = pd.DataFrame(timesheet_rows or [
        {"employee_id": "A", "post_id": "P1", "work_date": D("2026-01-05"), "hours": 8.0},
        {"employee_id": "A", "post_id": "P1", "work_date": D("2026-01-06"), "hours": 8.0},
    ], columns=["employee_id", "post_id", "work_date", "hours"])
    if payroll_rows is None:
        # Default: payroll that matches the timesheets week by week (Sunday start).
        payroll_rows = []
        weeks = timesheets.assign(week=timesheets["work_date"].map(
            lambda d: d - timedelta(days=(d.weekday() + 1) % 7)))
        for (employee, week), group in weeks.groupby(["employee_id", "week"]):
            payroll_rows.append({
                "employee_id": employee, "week_start": week,
                "week_end": week + timedelta(days=6),
                "regular_hours": float(group["hours"].sum()), "overtime_hours": 0.0,
                "paid_leave_hours": 0.0, "hourly_rate_paid": 17.5,
                "overtime_rate_paid": 26.25, "hw_paid": 0.0})
    payroll = pd.DataFrame(payroll_rows, columns=[
        "employee_id", "week_start", "week_end", "regular_hours", "overtime_hours",
        "paid_leave_hours", "hourly_rate_paid", "overtime_rate_paid", "hw_paid"])
    base = {"invoice_number": "I1", "invoice_period_start": D("2026-01-01"),
            "invoice_period_end": D("2026-01-31"), "line_type": "LINE"}
    rows = [{**base, **r} for r in invoice_rows]
    total = sum(r["line_amount"] for r in rows)
    rows.append({**base, "line_type": "TOTAL", "line_id": "TOTAL", "employee_id": "",
                 "post_id": "", "service_start": None, "service_end": None,
                 "hours_billed": 0.0, "unit_price": 0.0, "line_amount": total})
    return InvoiceData(contract, roster, timesheets, payroll, pd.DataFrame(rows))


def line(line_id="L1", employee="A", start="2026-01-05", end="2026-01-09", hours=16.0,
         price=10.0, amount=None):
    return {"line_id": line_id, "employee_id": employee, "post_id": "P1",
            "service_start": D(start), "service_end": D(end), "hours_billed": hours,
            "unit_price": price, "line_amount": hours * price if amount is None else amount}


def test_clean_invoice_has_no_findings(config):
    assert check_invoice(make_data([line()]), config) == []


def test_hours_within_tolerance_are_not_flagged(config):
    assert check_invoice(make_data([line(hours=16.25)]), config) == []


def test_overbilled_hours(config):
    findings = check_invoice(make_data([line(hours=20.0)]), config)
    assert [(f.rule_id, f.direction, f.difference) for f in findings] == [
        ("INV-02", "overbilled", 40.0)]


def test_underbilled_hours(config):
    findings = check_invoice(make_data([line(hours=8.0)]), config)
    assert [(f.rule_id, f.direction, f.difference) for f in findings] == [
        ("INV-02", "underbilled", -80.0)]


def test_stale_unit_price_after_price_change(config):
    timesheets = [{"employee_id": "A", "post_id": "P1", "work_date": D("2026-01-20"),
                   "hours": 8.0}]
    data = make_data([line(start="2026-01-19", end="2026-01-23", hours=8.0, price=10.0)],
                     timesheet_rows=timesheets)
    findings = check_invoice(data, config)
    assert [(f.rule_id, f.direction, f.difference) for f in findings] == [
        ("INV-04", "underbilled", -16.0)]


def test_line_crossing_a_price_change_is_flagged(config):
    timesheets = [
        {"employee_id": "A", "post_id": "P1", "work_date": D("2026-01-15"), "hours": 8.0},
        {"employee_id": "A", "post_id": "P1", "work_date": D("2026-01-16"), "hours": 8.0},
    ]
    data = make_data([line(start="2026-01-15", end="2026-01-16", hours=16.0, price=11.0)],
                     timesheet_rows=timesheets)
    findings = check_invoice(data, config)
    assert [f.rule_id for f in findings] == ["INV-04"]
    assert "crosses a contract price change" in findings[0].description


def test_negative_day_count(config):
    findings = check_invoice(make_data([line(start="2026-01-09", end="2026-01-05")]), config)
    assert [f.rule_id for f in findings] == ["INV-07"]
    assert "day count of -3" in findings[0].description


def test_employee_not_on_roster(config):
    findings = check_invoice(make_data([line(employee="Z")]), config)
    assert [(f.rule_id, f.direction, f.expected_amount) for f in findings] == [
        ("INV-01", "overbilled", 0.0)]


def test_employee_terminated_mid_period(config):
    roster = [{"contract_id": "C1", "employee_id": "A", "first_name": "x", "last_name": "y",
               "occupation_code": "11150", "occupation_title": "Janitor", "post_id": "P1",
               "hire_date": D("2025-01-01"), "termination_date": D("2026-01-05")}]
    findings = check_invoice(make_data([line()], roster_rows=roster), config)
    assert [(f.rule_id, f.expected_amount, f.difference) for f in findings] == [
        ("INV-01", 80.0, 80.0)]


def test_duplicate_line(config):
    findings = check_invoice(make_data([line("L1"), line("L2")]), config)
    assert [(f.rule_id, f.line_id, f.difference) for f in findings] == [
        ("INV-06", "L2", 160.0)]


def test_line_arithmetic_and_total(config):
    data = make_data([line(amount=170.0)])
    findings = check_invoice(data, config)
    assert [(f.rule_id, f.difference) for f in findings] == [("INV-08", 10.0)]
    data.invoice.loc[data.invoice["line_type"] == "TOTAL", "line_amount"] = 100.0
    findings = check_invoice(data, config)
    assert sorted((f.rule_id, f.line_id, f.direction) for f in findings) == [
        ("INV-08", "L1", "overbilled"), ("INV-08", "TOTAL", "underbilled")]


def test_headcount_above_contract(config):
    roster = [
        {"contract_id": "C1", "employee_id": e, "first_name": "x", "last_name": "y",
         "occupation_code": "11150", "occupation_title": "Janitor", "post_id": "P1",
         "hire_date": D("2025-01-01"), "termination_date": None} for e in ("A", "B")]
    timesheets = [
        {"employee_id": e, "post_id": "P1", "work_date": D(d), "hours": 8.0}
        for e in ("A", "B") for d in ("2026-01-05", "2026-01-06")]
    data = make_data([line("L1", "A"), line("L2", "B")], timesheet_rows=timesheets,
                     roster_rows=roster, headcount=1)
    findings = check_invoice(data, config)
    assert [(f.rule_id, f.direction) for f in findings] == [("INV-05", "overbilled")]


def test_payroll_hours_short_of_timesheet(config):
    payroll = [{"employee_id": "A", "week_start": D("2026-01-04"), "week_end": D("2026-01-10"),
                "regular_hours": 12.0, "overtime_hours": 0.0, "paid_leave_hours": 0.0,
                "hourly_rate_paid": 17.5, "overtime_rate_paid": 26.25, "hw_paid": 0.0}]
    findings = check_invoice(make_data([line()], payroll_rows=payroll), config)
    assert [(f.rule_id, f.direction, f.amount_owed_to_worker) for f in findings] == [
        ("INV-03", "underpaid_worker", 70.0)]


@pytest.mark.parametrize("missing", ["contract.csv", "invoice.csv"])
def test_missing_input_file_is_a_clear_error(tmp_path, sample_dir, missing):
    from labor_charge_verifier.common import InputError
    for f in sample_dir.glob("*.csv"):
        if f.name != missing:
            (tmp_path / f.name).write_bytes(f.read_bytes())
    with pytest.raises(InputError, match=missing):
        load_invoice_data(tmp_path)


# --------------------------------------------------------------------------
# Cases found in independent review
# --------------------------------------------------------------------------
def test_same_post_overlap_that_is_not_an_exact_duplicate_is_valued(config):
    findings = check_invoice(make_data([line("L1"), line("L2", amount=160.01)]), config)
    six = [f for f in findings if f.rule_id == "INV-06"]
    assert [(f.line_id, f.direction, f.difference) for f in six] == [("L2", "overbilled", 160.0)]
    over = sum(f.difference for f in findings if f.direction == "overbilled")
    assert round(over, 2) == 160.0  # the whole second line, not one cent


def test_hours_and_price_errors_on_one_line_add_up_to_the_true_difference(config):
    timesheets = [{"employee_id": "A", "post_id": "P1", "work_date": D("2026-01-20"),
                   "hours": 8.0}]
    data = make_data([line(start="2026-01-19", end="2026-01-23", hours=10.0, price=10.0)],
                     timesheet_rows=timesheets)
    findings = check_invoice(data, config)
    assert sorted(f.rule_id for f in findings) == ["INV-02", "INV-04"]
    # billed 10 h x 10.00 = 100.00; supported 8 h x 12.00 = 96.00
    assert round(sum(f.difference for f in findings), 2) == 4.0


def test_headcount_is_counted_day_by_day(config):
    roster = [
        {"contract_id": "C1", "employee_id": e, "first_name": "x", "last_name": "y",
         "occupation_code": "11150", "occupation_title": "Janitor", "post_id": "P1",
         "hire_date": D("2025-01-01"), "termination_date": None} for e in ("A", "B")]
    timesheets = [
        {"employee_id": "A", "post_id": "P1", "work_date": D("2026-01-05"), "hours": 8.0},
        {"employee_id": "A", "post_id": "P1", "work_date": D("2026-01-06"), "hours": 8.0},
        {"employee_id": "B", "post_id": "P1", "work_date": D("2026-01-06"), "hours": 8.0},
    ]
    data = make_data([line("L1", "A", "2026-01-05", "2026-01-06", 16.0),
                      line("L2", "B", "2026-01-06", "2026-01-06", 8.0)],
                     timesheet_rows=timesheets, roster_rows=roster, headcount=1)
    findings = [f for f in check_invoice(data, config) if f.rule_id == "INV-05"]
    assert [(f.period, f.direction) for f in findings] == [
        ("2026-01-06 to 2026-01-06", "overbilled")]
    assert findings[0].description.startswith("2 employees")


def test_timesheet_week_without_payroll_is_flagged(config):
    payroll = [{"employee_id": "A", "week_start": D("2025-12-28"), "week_end": D("2026-01-03"),
                "regular_hours": 0.0, "overtime_hours": 0.0, "paid_leave_hours": 0.0,
                "hourly_rate_paid": 17.5, "overtime_rate_paid": 26.25, "hw_paid": 0.0}]
    findings = check_invoice(make_data([line()], payroll_rows=payroll), config)
    assert [(f.rule_id, f.period) for f in findings] == [
        ("INV-03", "2026-01-04 to 2026-01-10")]


def _copy_sample(tmp_path, sample_dir):
    for f in sample_dir.glob("*.csv"):
        (tmp_path / f.name).write_bytes(f.read_bytes())
    return tmp_path


def test_duplicate_roster_employee_is_a_clear_error(tmp_path, sample_dir):
    from labor_charge_verifier.common import InputError
    folder = _copy_sample(tmp_path, sample_dir)
    roster = folder / "roster.csv"
    lines = roster.read_text().splitlines()
    roster.write_text("\n".join(lines + [lines[1]]) + "\n")
    with pytest.raises(InputError, match="must be unique"):
        load_invoice_data(folder)


@pytest.mark.parametrize("content,message", [
    ("", "empty"),
    ("invoice_number,invoice_period_start\n", "missing columns"),
])
def test_empty_or_header_only_files_are_clear_errors(tmp_path, sample_dir, content, message):
    from labor_charge_verifier.common import InputError
    folder = _copy_sample(tmp_path, sample_dir)
    (folder / "invoice.csv").write_text(content)
    with pytest.raises(InputError, match=message):
        load_invoice_data(folder)


def test_header_only_invoice_runs_without_crashing(tmp_path, sample_dir, config):
    folder = _copy_sample(tmp_path, sample_dir)
    header = (sample_dir / "invoice.csv").read_text().splitlines()[0]
    (folder / "invoice.csv").write_text(header + "\n")
    findings = check_invoice(load_invoice_data(folder), config)
    assert any(f.rule_id == "INV-08" and "no TOTAL row" in f.description for f in findings)


def test_blank_unit_price_is_an_error_not_zero(tmp_path, sample_dir):
    from labor_charge_verifier.common import InputError
    folder = _copy_sample(tmp_path, sample_dir)
    path = folder / "invoice.csv"
    lines = path.read_text().splitlines()
    cells = lines[1].split(",")
    cells[10] = ""
    lines[1] = ",".join(cells)
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(InputError, match="blank value in required column 'unit_price'"):
        load_invoice_data(folder)

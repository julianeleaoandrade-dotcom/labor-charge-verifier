from datetime import date

import pandas as pd

from labor_charge_verifier.wage_check import WageData, check_wages, load_wage_data

D = date.fromisoformat


def test_sample_data_produces_exactly_the_expected_findings(sample_dir, config):
    findings = check_wages(load_wage_data(sample_dir), config)
    got = sorted((f.rule_id, f.employee_id, f.period) for f in findings)
    weeks = ["2026-02-01 to 2026-02-07", "2026-02-08 to 2026-02-14",
             "2026-02-15 to 2026-02-21", "2026-02-22 to 2026-02-28"]
    expected = sorted(
        [("WAGE-01", "E004", w) for w in weeks]
        + [("WAGE-02", "E009", w) for w in weeks]
        + [("WAGE-03", "E015", weeks[1]), ("WAGE-04", "E019", "all weeks")])
    assert got == expected
    assert round(sum(f.amount_owed_to_worker or 0 for f in findings), 2) == 217.60


def make_data(rate=17.20, regular=40.0, overtime=0.0, ot_rate=None, hw=222.0,
              leave=0.0, occupation="11150"):
    contract = pd.DataFrame([{"contract_id": "C1", "contractor_name": "T", "wd_number": "WD1",
                              "post_id": "P1", "post_name": "Post", "occupation_code": "11150",
                              "required_headcount": "1", "billing_unit": "hour",
                              "unit_price": "30", "price_effective_start": D("2026-01-01"),
                              "price_effective_end": D("2026-12-31")}])
    roster = pd.DataFrame([{"contract_id": "C1", "employee_id": "A", "first_name": "x",
                            "last_name": "y", "occupation_code": occupation,
                            "occupation_title": "Janitor", "post_id": "P1",
                            "hire_date": D("2025-01-01"), "termination_date": None}])
    payroll = pd.DataFrame([{"employee_id": "A", "week_start": D("2026-01-04"),
                             "week_end": D("2026-01-10"), "regular_hours": regular,
                             "overtime_hours": overtime, "paid_leave_hours": leave,
                             "hourly_rate_paid": rate,
                             "overtime_rate_paid": rate * 1.5 if ot_rate is None else ot_rate,
                             "hw_paid": hw}])
    wd = pd.DataFrame([{"wd_number": "WD1", "revision": "1", "state": "ZZ", "area": "X",
                        "occupation_code": "11150", "occupation_title": "Janitor",
                        "hourly_rate": 17.20}])
    return WageData(contract, roster, payroll, wd)


def test_compliant_payroll_has_no_findings(config):
    assert check_wages(make_data(), config) == []


def test_rate_below_wd_reports_amount_owed(config):
    findings = check_wages(make_data(rate=16.80, hw=222.0), config)
    assert [(f.rule_id, f.amount_owed_to_worker) for f in findings] == [("WAGE-01", 16.0)]


def test_rate_below_wd_includes_overtime_premium(config):
    findings = check_wages(make_data(rate=16.80, overtime=10.0), config)
    # 40 x 0.40 + 10 x 0.40 x 1.5 = 16.00 + 6.00
    assert [(f.rule_id, f.amount_owed_to_worker) for f in findings] == [("WAGE-01", 22.0)]


def test_hw_short(config):
    findings = check_wages(make_data(hw=203.60), config)
    assert [(f.rule_id, f.amount_owed_to_worker) for f in findings] == [("WAGE-02", 18.4)]


def test_hw_counts_paid_leave_and_caps_at_40_hours(config):
    # 32 worked + 8 paid holiday = 40 hours paid -> 40 x 5.55 = 222.00 required
    findings = check_wages(make_data(regular=32.0, leave=8.0, hw=177.60), config)
    assert [(f.rule_id, f.amount_owed_to_worker) for f in findings] == [("WAGE-02", 44.4)]
    # 50 hours paid is still capped at 40 hours of H&W
    assert check_wages(make_data(regular=40.0, overtime=10.0, hw=222.0), config) == []


def test_overtime_paid_at_straight_time(config):
    findings = check_wages(make_data(rate=20.0, regular=48.0), config)
    assert [(f.rule_id, f.amount_owed_to_worker) for f in findings] == [("WAGE-03", 80.0)]


def test_overtime_rate_too_low(config):
    findings = check_wages(make_data(rate=20.0, overtime=5.0, ot_rate=25.0), config)
    assert [(f.rule_id, f.amount_owed_to_worker) for f in findings] == [("WAGE-03", 25.0)]


def test_occupation_not_on_wd_needs_conformance(config):
    findings = check_wages(make_data(rate=1.0, occupation="LEAD-01"), config)
    assert [f.rule_id for f in findings] == ["WAGE-04"]
    assert "conformance" in findings[0].description


def test_multiple_wd_revisions_are_refused(tmp_path, sample_dir):
    import pytest
    from labor_charge_verifier.common import InputError
    for f in sample_dir.glob("*.csv"):
        (tmp_path / f.name).write_bytes(f.read_bytes())
    wd = tmp_path / "wage_determination_SAMPLE.csv"
    wd.write_text(wd.read_text() + "SAMPLE-WD-0001,2,ZZ,Sample County,11150,Janitor,17.90\n")
    with pytest.raises(InputError, match="more than one revision"):
        load_wage_data(tmp_path)

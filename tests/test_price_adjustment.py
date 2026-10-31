from datetime import date

import pandas as pd
import pytest

from labor_charge_verifier.common import InputError
from labor_charge_verifier.price_adjustment import (
    allowable_wage_increase,
    compute_price_adjustment,
    load_price_adjustment_input,
    render_notice_letter,
)


def test_far_52_222_43_paragraph_d_example():
    """FAR 52.222-43(d): prior WD $4.00; contractor paid $4.10; new WD $4.50;
    contractor raises pay to $4.75. The allowable adjustment is $0.40 per hour."""
    assert allowable_wage_increase(4.00, 4.50, 4.10, 4.75) == pytest.approx(0.40)


@pytest.mark.parametrize("prior_wd,new_wd,prior_paid,new_paid,expected", [
    (17.20, 17.85, 17.20, 17.85, 0.65),   # paid exactly the WD before and after
    (17.20, 17.85, 17.50, 17.85, 0.35),   # already paid above the prior WD
    (19.40, 20.10, 20.00, 20.50, 0.10),   # part of the raise is voluntary
    (17.20, 17.85, 18.00, 18.00, 0.00),   # already above the new WD: nothing allowable
    (17.20, 17.85, 17.20, 17.50, 0.30),   # raise smaller than required: actual increase
])
def test_allowable_increase_cases(prior_wd, new_wd, prior_paid, new_paid, expected):
    assert allowable_wage_increase(prior_wd, new_wd, prior_paid, new_paid) == pytest.approx(expected)


def frame(**overrides):
    row = {"contract_id": "C1", "occupation_code": "11150", "occupation_title": "Janitor",
           "prior_wd_rate": 4.00, "new_wd_rate": 4.50, "prior_rate_paid": 4.10,
           "new_rate_paid": 4.75, "prior_hw_rate": 5.55, "new_hw_rate": 5.92, "prior_hw_paid": 5.55, "new_hw_paid": 5.92,
           "hours": 1000.0, "wd_received_date": date(2026, 9, 15)}
    row.update(overrides)
    return pd.DataFrame([row])


def test_worksheet_amounts(config):
    result = compute_price_adjustment(frame(), config, as_of=date(2026, 9, 20))
    row = result.worksheet.iloc[0]
    assert row["allowable_wage_increase_per_hour"] == pytest.approx(0.40)
    assert row["wage_increase_amount"] == pytest.approx(400.00)
    assert row["hw_increase_amount"] == pytest.approx(370.00)
    # Taxes and insurance: 6.2 + 1.45 + 0.6 + 2.7 + 3.5 = 14.45% of the wage increase only
    assert row["payroll_tax_and_insurance_amount"] == pytest.approx(57.80)
    assert row["total_adjustment"] == pytest.approx(827.80)


def test_deadline_open_and_passed(config):
    open_result = compute_price_adjustment(frame(), config, as_of=date(2026, 10, 1))
    assert open_result.deadlines[0]["deadline"] == date(2026, 10, 15)
    assert open_result.deadlines[0]["status"] == "open"
    assert open_result.deadlines[0]["days_left"] == 14
    assert not open_result.warnings
    late = compute_price_adjustment(frame(), config, as_of=date(2026, 10, 30))
    assert late.deadlines[0]["status"] == "passed"
    assert any("ended on 2026-10-15" in w for w in late.warnings)


def test_rate_below_new_wd_is_warned(config):
    result = compute_price_adjustment(frame(new_rate_paid=4.40), config,
                                      as_of=date(2026, 9, 20))
    assert any("below the new WD" in w for w in result.warnings)


@pytest.mark.parametrize("column", ["overhead_rate", "G&A", "general_and_administrative",
                                    "profit", "fee_percent", "markup"])
def test_overhead_ga_and_profit_are_refused(tmp_path, sample_dir, config, column):
    source = (sample_dir / "price_adjustment_input.csv").read_text().splitlines()
    source[0] += f",{column}"
    source[1:] = [line + ",0.10" for line in source[1:]]
    path = tmp_path / "input.csv"
    path.write_text("\n".join(source) + "\n")
    with pytest.raises(InputError, match="52.222-43\\(e\\)"):
        load_price_adjustment_input(path, config)


def test_sample_input_runs(sample_dir, config):
    data = load_price_adjustment_input(sample_dir / "price_adjustment_input.csv", config)
    result = compute_price_adjustment(data, config, as_of=date(2026, 10, 30))
    by_code = result.worksheet.set_index("occupation_code")
    assert by_code.loc["11150", "allowable_wage_increase_per_hour"] == pytest.approx(0.35)
    assert by_code.loc["11210", "allowable_wage_increase_per_hour"] == pytest.approx(0.55)
    assert by_code.loc["27101", "allowable_wage_increase_per_hour"] == pytest.approx(0.10)
    assert result.total_adjustment == pytest.approx(27358.40)
    letter = render_notice_letter(result)
    assert "paragraph (f)" in letter
    assert "27,358.40" in letter
    assert "overhead or profit" in letter


def test_hw_adjustment_uses_actual_hw_increase(config):
    # Contractor already paid 5.80 H&W before the new WD (5.92): only 0.12 is allowable.
    result = compute_price_adjustment(frame(prior_hw_paid=5.80, new_hw_paid=6.00), config,
                                      as_of=date(2026, 9, 20))
    row = result.worksheet.iloc[0]
    assert row["allowable_hw_increase_per_hour"] == pytest.approx(0.12)
    assert row["hw_increase_amount"] == pytest.approx(120.00)


def test_blank_received_date_next_to_real_dates_does_not_crash(config):
    data = pd.concat([frame(), frame(occupation_code="27101", wd_received_date=None)],
                     ignore_index=True)
    result = compute_price_adjustment(data, config, as_of=date(2026, 9, 20))
    assert len(result.deadlines) == 1
    assert any("no wd_received_date" in w for w in result.warnings)


def test_invalid_as_of_is_a_clear_error(sample_dir, capsys):
    from labor_charge_verifier.cli import main
    code = main(["price-adjustment", "--input", str(sample_dir / "price_adjustment_input.csv"),
                 "--out", str(sample_dir.parent / "reports"), "--as-of", "30/10/2026"])
    assert code == 2
    assert "YYYY-MM-DD" in capsys.readouterr().err

from datetime import date
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from labor_charge_verifier.common import InputError
from labor_charge_verifier.invoice_check import check_invoice, load_invoice_data
from labor_charge_verifier.wage_check import check_wages, load_wage_data
from labor_charge_verifier.workbook import SHEETS, workbook_to_csv_texts, workbook_to_folder

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_BOOK = ROOT / "sample-data" / "sample-workbook.xlsx"
TEMPLATE_BOOK = ROOT / "templates" / "labor-charge-verifier-template.xlsx"


def test_sample_workbook_gives_the_same_findings_as_the_csv_files(tmp_path, sample_dir, config):
    workbook_to_folder(SAMPLE_BOOK, tmp_path)
    from_book = check_invoice(load_invoice_data(tmp_path), config)
    from_csv = check_invoice(load_invoice_data(sample_dir), config)
    assert [f.to_dict() for f in from_book] == [f.to_dict() for f in from_csv]
    wages_book = check_wages(load_wage_data(tmp_path), config)
    wages_csv = check_wages(load_wage_data(sample_dir), config)
    assert [f.to_dict() for f in wages_book] == [f.to_dict() for f in wages_csv]


def test_template_has_every_sheet_with_the_csv_headers():
    texts = workbook_to_csv_texts(TEMPLATE_BOOK)
    assert set(texts) == set(SHEETS.values())
    for file_name, text in texts.items():
        template_csv = (ROOT / "templates" / file_name).read_text().splitlines()
        header = [line for line in template_csv if not line.startswith("#")][0]
        assert text.splitlines() == [header], file_name


def test_workbooks_are_up_to_date_with_the_csv_files(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_workbooks",
                                                  ROOT / "scripts" / "build_workbooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for template, committed in ((True, TEMPLATE_BOOK), (False, SAMPLE_BOOK)):
        fresh = tmp_path / committed.name
        module.build(template, fresh)
        assert workbook_to_csv_texts(fresh) == workbook_to_csv_texts(committed), committed.name


def make_book(path, sheets):
    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    book.save(path)
    return path


def test_cell_values_are_converted_like_a_csv(tmp_path):
    path = make_book(tmp_path / "b.xlsx", {
        "Notes": [["anything"]],
        " timesheets ": [
            ["# guidance line"],
            ["employee_id", "post_id", "work_date", "hours"],
            [],
            ["E001", "P01", date(2026, 2, 2), 8.0],
            [1001, "P01", "2026-02-03", 7.5],
        ],
    })
    texts = workbook_to_csv_texts(path)
    assert list(texts) == ["timesheets.csv"]
    assert texts["timesheets.csv"].splitlines() == [
        "employee_id,post_id,work_date,hours",
        "E001,P01,2026-02-02,8",
        "1001,P01,2026-02-03,7.5",
    ]


def test_workbook_without_known_sheets_is_a_clear_error(tmp_path):
    path = make_book(tmp_path / "b.xlsx", {"Sheet1": [["a", "b"]]})
    with pytest.raises(InputError, match="no worksheet with a known name"):
        workbook_to_csv_texts(path)


def test_file_that_is_not_a_workbook_is_a_clear_error(tmp_path):
    path = tmp_path / "fake.xlsx"
    path.write_text("not really excel")
    with pytest.raises(InputError, match="could not be opened as an Excel workbook"):
        workbook_to_csv_texts(path)


def test_cli_accepts_a_workbook(tmp_path, capsys):
    from labor_charge_verifier.cli import main
    assert main(["check-invoice", "--data", str(SAMPLE_BOOK), "--out", str(tmp_path)]) == 0
    assert "14 findings" in capsys.readouterr().out
    assert main(["price-adjustment", "--input", str(SAMPLE_BOOK), "--out", str(tmp_path),
                 "--as-of", "2026-10-01"]) == 0
    assert "27,358.40" in capsys.readouterr().out


def test_sample_workbook_marks_the_wage_determination_as_sample():
    sheet = load_workbook(SAMPLE_BOOK)["Wage determination"]
    assert "SAMPLE - NOT A REAL WAGE DETERMINATION" in str(sheet["A2"].value)

"""Build the Excel workbooks from the CSV files in the repository.

- templates/labor-charge-verifier-template.xlsx: blank workbook with an
  instructions sheet and one worksheet per input, ready to fill in.
- sample-data/sample-workbook.xlsx: the same layout filled with the
  fictitious sample data, so the workbook gives the same findings as the CSVs.

The CSV files stay the source of truth; run this script after changing them.

Usage: python scripts/build_workbooks.py
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]

# (worksheet, csv file, one row per, used by)
SHEETS = [
    ("Contract", "contract.csv", "post and price period", "Invoice check, wage check"),
    ("Roster", "roster.csv", "employee on the contract", "Invoice check, wage check"),
    ("Timesheets", "timesheets.csv", "employee, post and day worked", "Invoice check"),
    ("Payroll", "payroll.csv", "employee and workweek", "Invoice check, wage check"),
    ("Invoice", "invoice.csv", "invoice line, plus one TOTAL row", "Invoice check"),
    ("Wage determination", "wage_determination.csv", "occupation on the wage determination",
     "Wage check"),
    ("Price adjustment", "price_adjustment_input.csv", "occupation", "Price adjustment"),
]
SAMPLE_FILES = {"wage_determination.csv": "wage_determination_SAMPLE.csv"}

DESCRIPTIONS = {
    "contract_id": "Contract identifier.",
    "contractor_name": "Contractor's name.",
    "wd_number": "Number of the wage determination incorporated in the contract.",
    "post_id": "Post or labor category code, e.g. P01.",
    "post_name": "Description of the post.",
    "occupation_code": "Occupation code from the wage determination, e.g. 11150.",
    "occupation_title": "Occupation title, e.g. Janitor.",
    "required_headcount": "Number of people the contract authorizes on the post.",
    "billing_unit": "Unit billed. This version supports: hour.",
    "unit_price": "Contract price per hour (USD).",
    "price_effective_start": "First day this price applies (date).",
    "price_effective_end": "Last day this price applies (date).",
    "employee_id": "Employee ID. Do not use Social Security numbers.",
    "first_name": "Optional. May be left blank.",
    "last_name": "Optional. May be left blank.",
    "hire_date": "First day employed on the contract (date).",
    "termination_date": "Last day employed (date). Blank if still employed.",
    "work_date": "Day worked (date).",
    "hours": "Hours. On Timesheets: hours worked that day.",
    "week_start": "First day of the workweek (date). All weeks start on the same weekday.",
    "week_end": "Last day of the workweek (date).",
    "regular_hours": "Hours paid at the regular rate.",
    "overtime_hours": "Hours paid at the overtime rate.",
    "paid_leave_hours": "Paid vacation, holiday or sick hours. 0 if none.",
    "hourly_rate_paid": "Regular hourly rate paid (USD).",
    "overtime_rate_paid": "Overtime hourly rate paid (USD).",
    "hw_paid": "Health and welfare paid for the week, cash or plan contributions (USD).",
    "invoice_number": "Invoice number.",
    "invoice_period_start": "First day of the billing period (date).",
    "invoice_period_end": "Last day of the billing period (date).",
    "line_type": "LINE for an invoice line; TOTAL for the one row with the invoice total.",
    "line_id": "Line identifier, e.g. L001. Use TOTAL on the total row.",
    "service_start": "First day covered by the line (date).",
    "service_end": "Last day covered by the line (date).",
    "hours_billed": "Hours billed on the line. Blank on the TOTAL row.",
    "line_amount": "Amount billed on the line, or the stated total on the TOTAL row (USD).",
    "revision": "Revision number of the wage determination.",
    "state": "State on the wage determination.",
    "area": "Area or county on the wage determination.",
    "hourly_rate": "Minimum hourly wage rate on the wage determination (USD).",
    "prior_wd_rate": "Wage rate on the prior wage determination (USD/hour).",
    "new_wd_rate": "Wage rate on the new wage determination (USD/hour).",
    "prior_rate_paid": "Rate actually paid before the new wage determination (USD/hour).",
    "new_rate_paid": "Rate actually paid after the new wage determination (USD/hour).",
    "prior_hw_rate": "Health and welfare rate on the prior wage determination (USD/hour).",
    "new_hw_rate": "Health and welfare rate on the new wage determination (USD/hour).",
    "prior_hw_paid": "Health and welfare actually paid before (USD/hour).",
    "new_hw_paid": "Health and welfare actually paid after (USD/hour).",
    "wd_received_date": "Date the new wage determination was received.",
}
DATE_COLUMNS = {"price_effective_start", "price_effective_end", "hire_date", "termination_date",
                "work_date", "week_start", "week_end", "invoice_period_start",
                "invoice_period_end", "service_start", "service_end", "wd_received_date"}
TEXT_COLUMNS = {"contract_id", "contractor_name", "wd_number", "post_id", "post_name",
                "occupation_code", "occupation_title", "billing_unit", "employee_id",
                "first_name", "last_name", "invoice_number", "line_type", "line_id",
                "revision", "state", "area"}
MONEY_COLUMNS = {"unit_price", "hourly_rate_paid", "overtime_rate_paid", "hw_paid",
                 "line_amount", "hourly_rate", "prior_wd_rate", "new_wd_rate",
                 "prior_rate_paid", "new_rate_paid", "prior_hw_rate", "new_hw_rate",
                 "prior_hw_paid", "new_hw_paid"}

HEADER_FILL = PatternFill("solid", fgColor="1F5F99")
HEADER_FONT = Font(bold=True, color="FFFFFF")
GUIDE_FONT = Font(italic=True, color="59636E")
TEMPLATE_ROWS = 500


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
    rows = list(csv.reader(lines))
    return rows[0], rows[1:]


def typed(column: str, value: str):
    if value == "":
        return None
    if column in DATE_COLUMNS:
        return date.fromisoformat(value)
    if column in TEXT_COLUMNS:
        return value
    try:
        number = float(value)
    except ValueError:
        return value
    return int(number) if number.is_integer() and column not in MONEY_COLUMNS else number


def add_data_sheet(book: Workbook, title: str, header: list[str], rows: list[list[str]],
                   per_row: str, banner: str | None, template: bool) -> None:
    sheet = book.create_sheet(title)
    guide = f"# One row per {per_row}. Keep this header row as it is. " \
            "Lines starting with # are ignored."
    sheet.append([guide])
    sheet["A1"].font = GUIDE_FONT
    if banner:
        sheet.append([banner])
        sheet.cell(sheet.max_row, 1).font = Font(bold=True, color="9A2D1F")
    sheet.append(header)
    header_row = sheet.max_row
    for index, column in enumerate(header, 1):
        cell = sheet.cell(header_row, index)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.comment = Comment(DESCRIPTIONS.get(column, column), "labor-charge-verifier",
                               width=260, height=90)
        sheet.column_dimensions[get_column_letter(index)].width = max(14, len(column) + 4)
    for values in rows:
        sheet.append([typed(c, v) for c, v in zip(header, values)])
    last_row = header_row + (TEMPLATE_ROWS if template else max(len(rows), 1))
    for index, column in enumerate(header, 1):
        letter = get_column_letter(index)
        fmt = ("yyyy-mm-dd" if column in DATE_COLUMNS else
               "#,##0.00" if column in MONEY_COLUMNS else
               "@" if column in TEXT_COLUMNS else None)
        if fmt:
            for row in range(header_row + 1, last_row + 1):
                sheet[f"{letter}{row}"].number_format = fmt
        if column in DATE_COLUMNS:
            rule = DataValidation(type="date", operator="greaterThan", formula1="DATE(2000,1,1)",
                                  allow_blank=True, showErrorMessage=True,
                                  errorTitle="Date expected",
                                  error="Enter a date, for example 2026-02-01.")
            sheet.add_data_validation(rule)
            rule.add(f"{letter}{header_row + 1}:{letter}{last_row}")
        if column == "line_type":
            rule = DataValidation(type="list", formula1='"LINE,TOTAL"', allow_blank=True,
                                  showErrorMessage=True, errorTitle="LINE or TOTAL",
                                  error="Use LINE for invoice lines and TOTAL for the total row.")
            sheet.add_data_validation(rule)
            rule.add(f"{letter}{header_row + 1}:{letter}{last_row}")
    sheet.freeze_panes = sheet.cell(header_row + 1, 1)


def add_instructions(book: Workbook, sample: bool) -> None:
    sheet = book.active
    sheet.title = "Instructions"
    sheet.column_dimensions["A"].width = 24
    sheet.column_dimensions["B"].width = 44
    sheet.column_dimensions["C"].width = 30
    title = ("labor-charge-verifier - SAMPLE workbook (fictitious data)" if sample
             else "labor-charge-verifier - input workbook")
    lines = [
        (title, Font(bold=True, size=14)),
        ("", None),
        ("How to use this workbook", Font(bold=True)),
        ("1. Fill in the worksheets you need (see the table below). One row per record.", None),
        ("2. Keep the sheet names and the header row exactly as they are. Hover over a "
         "header to see what goes in the column.", None),
        ("3. Enter dates as dates (for example 2026-02-01) and amounts as numbers.", None),
        ("4. Use employee IDs, not names or Social Security numbers.", None),
        ("5. Save as Excel Workbook (.xlsx). Then open the web page, choose this file and "
         "click Run.", None),
        ("", None),
    ]
    if sample:
        lines.insert(1, ("All data in this workbook is invented for testing. The wage "
                         "determination is a SAMPLE, not a real wage determination.",
                         Font(bold=True, color="9A2D1F")))
    for text, font in lines:
        sheet.append([text])
        if font:
            sheet.cell(sheet.max_row, 1).font = font
    sheet.append(["Worksheet", "One row per", "Used by"])
    for cell in sheet[sheet.max_row]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for title_, _, per_row, used_by in SHEETS:
        sheet.append([title_, per_row, used_by])
    sheet.append([])
    sheet.append(["Web page: https://julianeleaoandrade-dotcom.github.io/labor-charge-verifier/"])
    sheet.append(["Column reference: https://github.com/julianeleaoandrade-dotcom/"
                  "labor-charge-verifier/blob/main/docs/data-format.md"])
    sheet.append(["Every finding is a lead for a person to review, not a conclusion. "
                  "General information, not legal or accounting advice."])


def build(template: bool, out: Path) -> None:
    book = Workbook()
    add_instructions(book, sample=not template)
    for title, csv_name, per_row, _ in SHEETS:
        if template:
            header, _ = read_csv(ROOT / "templates" / csv_name)
            rows = []
        else:
            header, rows = read_csv(ROOT / "sample-data" / SAMPLE_FILES.get(csv_name, csv_name))
        banner = ("# SAMPLE - NOT A REAL WAGE DETERMINATION. Rates are invented for testing."
                  if title == "Wage determination" and not template else None)
        add_data_sheet(book, title, header, rows, per_row, banner, template)
    book.properties.creator = "labor-charge-verifier"
    book.properties.title = title_for(template)
    book.save(out)
    print(f"Wrote {out}")


def title_for(template: bool) -> str:
    return "labor-charge-verifier input template" if template else "labor-charge-verifier sample"


if __name__ == "__main__":
    build(True, ROOT / "templates" / "labor-charge-verifier-template.xlsx")
    build(False, ROOT / "sample-data" / "sample-workbook.xlsx")

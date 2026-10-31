"""Read a single Excel workbook (.xlsx) instead of separate CSV files.

Each worksheet holds what one CSV file would hold, with the same column
headers in row 1. The workbook is converted to CSV files in a folder, and the
checks then run on that folder exactly as they do on CSV files, so both input
formats follow one code path.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time
from pathlib import Path

from .common import InputError

# Worksheet name -> CSV file name. Worksheet names are matched ignoring case
# and surrounding spaces.
SHEETS = {
    "Contract": "contract.csv",
    "Roster": "roster.csv",
    "Timesheets": "timesheets.csv",
    "Payroll": "payroll.csv",
    "Invoice": "invoice.csv",
    "Wage determination": "wage_determination.csv",
    "Price adjustment": "price_adjustment_input.csv",
}


def is_workbook(path: str | Path) -> bool:
    return Path(path).suffix.lower() in (".xlsx", ".xlsm")


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        raise InputError(f"A cell contains a time ({value}) where a date or number was expected.")
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return repr(round(value, 10))
    return str(value).strip()


def workbook_to_csv_texts(path: str | Path) -> dict[str, str]:
    """Return {csv file name: CSV text} for each known worksheet that has a
    header row. Blank rows and rows whose first cell starts with "#" are
    skipped. Unknown worksheets (for example the
    instructions sheet) are ignored."""
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise InputError("Reading Excel files needs the 'openpyxl' package "
                         "(pip install openpyxl).") from exc
    path = Path(path)
    if not path.is_file():
        raise InputError(f"Missing input file: {path}")
    try:
        book = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        raise InputError(f"{path.name}: could not be opened as an Excel workbook (.xlsx). "
                         "Save it from Excel as 'Excel Workbook (*.xlsx)'.") from exc
    by_name = {name.strip().lower(): name for name in book.sheetnames}
    result: dict[str, str] = {}
    try:
        for sheet_name, file_name in SHEETS.items():
            actual = by_name.get(sheet_name.lower())
            if actual is None:
                continue
            rows = []
            for row in book[actual].iter_rows(values_only=True):
                cells = [_cell_text(v) for v in row]
                if not any(cells):
                    continue
                if cells[0].startswith("#"):  # guidance lines, as in CSV files
                    continue
                rows.append(cells)
            if not rows:
                continue
            header = rows[0]
            while header and header[-1] == "":
                header.pop()
            width = len(header)
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow(header)
            for cells in rows[1:]:
                writer.writerow((cells + [""] * width)[:width])
            result[file_name] = buffer.getvalue()
    finally:
        book.close()
    if not result:
        expected = ", ".join(f"'{s}'" for s in SHEETS)
        raise InputError(f"{path.name}: no worksheet with a known name was found. "
                         f"Expected worksheets named {expected}.")
    return result


def workbook_to_folder(path: str | Path, out_dir: str | Path) -> list[str]:
    """Write one CSV file per known worksheet into ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = workbook_to_csv_texts(path)
    for file_name, text in texts.items():
        (out_dir / file_name).write_text(text, encoding="utf-8")
    return sorted(texts)

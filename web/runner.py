"""Glue between the browser page (web/app.js) and the labor_charge_verifier
package. It runs inside the browser with Pyodide and calls the same functions
as the command-line tool. Every function takes and returns JSON strings."""

from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

from labor_charge_verifier import __version__
from labor_charge_verifier.common import InputError, load_config
from labor_charge_verifier.invoice_check import check_invoice, load_invoice_data
from labor_charge_verifier.price_adjustment import (SUPPORTING_DOCUMENTS, compute_price_adjustment,
                                                    describe_deadline,
                                                    load_price_adjustment_input,
                                                    render_notice_letter)
from labor_charge_verifier.report import (HTML_STYLE, findings_frame, render_html,
                                          render_markdown, summarize)
from labor_charge_verifier.wage_check import check_wages, load_wage_data
from labor_charge_verifier.workbook import SHEETS, workbook_to_csv_texts

CONFIG_PATH = Path("/lcv/config/settings.example.yaml")

# Settings the page lets the user change: (label, section, key).
EDITABLE = {
    "hw_rate": ("health_and_welfare", "rate_per_hour"),
    "hours_tolerance": ("tolerances", "hours"),
    "suta": ("payroll_tax_rates", "suta"),
    "workers_compensation": ("payroll_tax_rates", "workers_compensation"),
}


def _set(config: dict, section: str, key: str, value: float) -> None:
    current = config[section][key]
    if isinstance(current, dict) and "value" in current:
        current["value"] = value
        current["source"] = "Changed by the user in the browser page"
    else:
        config[section][key] = value


def _get(config: dict, section: str, key: str):
    current = config[section][key]
    return current["value"] if isinstance(current, dict) and "value" in current else current


def _config(overrides_json: str) -> dict:
    config = load_config(CONFIG_PATH)
    overrides = json.loads(overrides_json or "{}")
    for name, (section, key) in EDITABLE.items():
        if overrides.get(name) not in (None, ""):
            try:
                value = float(overrides[name])
            except ValueError as exc:
                raise InputError(f"Setting '{name}' must be a number.") from exc
            if value < 0:
                raise InputError(f"Setting '{name}' cannot be negative.")
            _set(config, section, key, value)
    return config


def defaults() -> str:
    config = load_config(CONFIG_PATH)
    values = {name: _get(config, s, k) for name, (s, k) in EDITABLE.items()}
    values["version"] = __version__
    return json.dumps(values)


def _findings_result(findings, title: str, stem: str) -> dict:
    frame = findings_frame(findings)
    return {
        "ok": True,
        "summary": summarize(frame),
        "report_html": render_html(title, frame, "files selected in the browser"),
        "downloads": {
            f"{stem}_findings.csv": frame.to_csv(index=False),
            f"{stem}_report.md": render_markdown(title, frame, "files selected in the browser"),
            f"{stem}_report.html": render_html(title, frame, "files selected in the browser"),
        },
    }


def _guard(func):
    def wrapper(*args):
        try:
            return json.dumps(func(*args))
        except InputError as exc:
            return json.dumps({"ok": False, "error": str(exc)})
        except Exception as exc:  # shown to the user instead of a silent failure
            return json.dumps({"ok": False, "error": f"Unexpected error: {exc!r}. "
                               "Check that each file matches docs/data-format.md."})
    return wrapper


@_guard
def convert_workbook(path: str) -> dict:
    files = workbook_to_csv_texts(path)
    names = {csv_name: sheet for sheet, csv_name in SHEETS.items()}
    return {"ok": True, "files": files, "sheet_names": {k: names[k] for k in files}}


@_guard
def run_invoice(data_dir: str, overrides_json: str) -> dict:
    config = _config(overrides_json)
    findings = check_invoice(load_invoice_data(data_dir), config)
    return _findings_result(findings, "Invoice vs. records - findings", "invoice_check")


@_guard
def run_wages(data_dir: str, overrides_json: str) -> dict:
    config = _config(overrides_json)
    findings = check_wages(load_wage_data(data_dir), config)
    return _findings_result(findings, "Wage-determination compliance - findings", "wage_check")


@_guard
def run_price(input_path: str, overrides_json: str, as_of: str) -> dict:
    config = _config(overrides_json)
    try:
        as_of_date = date.fromisoformat(as_of) if as_of else None
    except ValueError as exc:
        raise InputError("The 'as of' date must be a valid date.") from exc
    frame = load_price_adjustment_input(input_path, config)
    result = compute_price_adjustment(frame, config, as_of=as_of_date)
    esc = html.escape
    columns = {
        "occupation_title": "Occupation",
        "allowable_wage_increase_per_hour": "Allowable wage increase / hour",
        "allowable_hw_increase_per_hour": "Allowable H&W increase / hour",
        "hours": "Hours",
        "wage_increase_amount": "Wage",
        "hw_increase_amount": "H&W",
        "payroll_tax_and_insurance_amount": "Taxes and insurance",
        "total_adjustment": "Total",
        "notes": "Notes",
    }
    rows = []
    for _, row in result.worksheet.iterrows():
        cells = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                text = f"{value:,.0f}" if column == "hours" else f"{value:,.2f}"
                cells.append(f"<td class='num'>{text}</td>")
            else:
                cells.append(f"<td>{esc(str(value))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    deadlines = "".join(
        f"<li>WD received {d['wd_received_date']}: notice due by "
        f"<strong>{d['deadline']}</strong> ({esc(describe_deadline(d))}).</li>"
        for d in result.deadlines)
    warnings = "".join(f"<li>{esc(w)}</li>" for w in result.warnings)
    page = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>FAR 52.222-43 worksheet</title><style>{HTML_STYLE}</style></head><body>"
        "<h1>FAR 52.222-43 price adjustment worksheet</h1>"
        f"<p class='note'>labor-charge-verifier {__version__}. General information, not legal "
        "or accounting advice.</p><table><tr>"
        + "".join(f"<th>{esc(h)}</th>" for h in columns.values()) + "</tr>"
        + "".join(rows) + "</table>"
        f"<p><strong>Total adjustment: {result.total_adjustment:,.2f}</strong>. Payroll tax and "
        f"insurance rate applied: {result.tax_rate_total * 100:.2f}%. No overhead, G&amp;A or "
        "profit is included (FAR 52.222-43(e)).</p>"
        f"<h2>Notice deadline (FAR 52.222-43(f))</h2><ul>{deadlines or '<li>No date given.</li>'}</ul>"
        + (f"<h2>Warnings</h2><ul>{warnings}</ul>" if warnings else "")
        + "</body></html>")
    documents = "\n".join(["# Supporting records to attach and keep", ""]
                          + [f"- [ ] {d}" for d in SUPPORTING_DOCUMENTS]) + "\n"
    return {
        "ok": True,
        "summary": {"total_adjustment": result.total_adjustment,
                    "deadlines": [describe_deadline(d) for d in result.deadlines],
                    "warnings": result.warnings},
        "report_html": page,
        "downloads": {
            "price_adjustment_worksheet.csv": result.worksheet.to_csv(index=False),
            "price_adjustment_notice_DRAFT.md": render_notice_letter(result),
            "price_adjustment_supporting_documents.md": documents,
            "price_adjustment_report.html": page,
        },
    }

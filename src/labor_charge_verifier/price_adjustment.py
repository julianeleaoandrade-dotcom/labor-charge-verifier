"""Module 3 - FAR 52.222-43 price-adjustment worksheet.

Builds the per-occupation worksheet behind a price-adjustment request after a
new wage determination (WD) takes effect on a multiple-year or option
contract, a draft notice to the contracting officer, and a list of supporting
records.

How the allowable wage increase is computed follows the example in
FAR 52.222-43(d): prior WD $4.00, contractor paid $4.10, new WD $4.50,
contractor raises pay to $4.75 -> allowable adjustment $0.40 per hour.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .common import InputError, cfg, read_csv, to_float

INPUT_COLUMNS = ["contract_id", "occupation_code", "occupation_title",
                 "prior_wd_rate", "new_wd_rate", "prior_rate_paid", "new_rate_paid",
                 "prior_hw_rate", "new_hw_rate", "prior_hw_paid", "new_hw_paid",
                 "hours", "wd_received_date"]
NUMERIC_COLUMNS = ["prior_wd_rate", "new_wd_rate", "prior_rate_paid", "new_rate_paid",
                   "prior_hw_rate", "new_hw_rate", "prior_hw_paid", "new_hw_paid", "hours"]

EXCLUSION_MESSAGE = (
    "FAR 52.222-43(e) limits the adjustment to increases in wages and fringe "
    "benefits and the accompanying increases in Social Security and "
    "unemployment taxes and workers' compensation insurance. It excludes "
    "general and administrative costs, overhead and profit. Remove these "
    "columns and run again."
)


def allowable_wage_increase(prior_wd_rate: float, new_wd_rate: float,
                            prior_rate_paid: float, new_rate_paid: float) -> float:
    """Allowable increase per hour under FAR 52.222-43(d).

    The lower of the actual increase in the rate paid and the increase needed
    to bring the rate previously paid up to the new WD rate, never below zero.
    ``prior_wd_rate`` is accepted so callers pass the full set of facts; when
    the contractor already paid above the prior WD, the higher rate actually
    paid is the starting point.
    """
    actual_increase = new_rate_paid - prior_rate_paid
    starting_point = max(prior_rate_paid, prior_wd_rate)
    required_increase = max(0.0, new_wd_rate - starting_point)
    return round(max(0.0, min(actual_increase, required_increase)), 4)


def find_forbidden_columns(columns: list[str], terms: list[str]) -> list[str]:
    hits = []
    for column in columns:
        lowered = column.lower().replace("g&a", "g_and_a").replace("g/a", "g_and_a")
        tokens = re.split(r"[^a-z0-9]+", lowered)
        if "ga" in tokens:  # e.g. "ga", "ga_rate"
            hits.append(column)
            continue
        normalized = re.sub(r"[^a-z0-9]", "", lowered)
        for term in terms:
            if re.sub(r"[^a-z0-9]", "", term.lower()) in normalized:
                hits.append(column)
                break
    return hits


@dataclass
class PriceAdjustmentResult:
    worksheet: pd.DataFrame
    deadlines: list[dict]
    warnings: list[str] = field(default_factory=list)
    total_adjustment: float = 0.0
    tax_rate_total: float = 0.0


def load_price_adjustment_input(path: str | Path, config: dict) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise InputError(f"Missing input file: {path}")
    header = pd.read_csv(path, nrows=0).columns.tolist()
    forbidden = find_forbidden_columns(header, cfg(config, "price_adjustment",
                                                   "forbidden_cost_terms"))
    if forbidden:
        raise InputError(f"Input contains cost columns that are not allowed: "
                         f"{forbidden}. {EXCLUSION_MESSAGE}")
    frame = read_csv(path, INPUT_COLUMNS, ["wd_received_date"])
    return to_float(frame, NUMERIC_COLUMNS, path.name)


def compute_price_adjustment(frame: pd.DataFrame, config: dict,
                             as_of: date | None = None) -> PriceAdjustmentResult:
    as_of = as_of or date.today()
    notice_days = int(cfg(config, "price_adjustment", "notice_days"))
    taxes_on_hw = bool(cfg(config, "price_adjustment", "apply_taxes_to_health_and_welfare"))
    tax_rates = {key: float(cfg(config, "payroll_tax_rates", key))
                 for key in ("social_security", "medicare", "futa", "suta",
                             "workers_compensation")}
    tax_rate_total = sum(tax_rates.values()) / 100.0

    rows, warnings = [], []
    for _, item in frame.iterrows():
        notes = []
        allowed = allowable_wage_increase(item["prior_wd_rate"], item["new_wd_rate"],
                                          item["prior_rate_paid"], item["new_rate_paid"])
        actual = item["new_rate_paid"] - item["prior_rate_paid"]
        required = max(0.0, item["new_wd_rate"] - max(item["prior_rate_paid"],
                                                      item["prior_wd_rate"]))
        if item["new_rate_paid"] < item["new_wd_rate"]:
            notes.append("Rate now paid is below the new WD rate; correct pay before "
                         "requesting an adjustment.")
            warnings.append(f"{item['occupation_title']}: rate paid "
                            f"{item['new_rate_paid']:,.2f} is below the new WD rate "
                            f"{item['new_wd_rate']:,.2f}.")
        if item["prior_rate_paid"] > item["prior_wd_rate"]:
            notes.append("Contractor already paid above the prior WD; only the increase "
                         "needed to reach the new WD is allowable.")
        if actual > required and required > 0:
            notes.append("Part of the raise given is voluntary and is not allowable.")
        hours = item["hours"]
        wage_amount = round(allowed * hours, 2)
        # PA-02: same rule as wages - the actual H&W increase made to comply.
        hw_increase = allowable_wage_increase(item["prior_hw_rate"], item["new_hw_rate"],
                                              item["prior_hw_paid"], item["new_hw_paid"])
        if item["new_hw_paid"] < item["new_hw_rate"]:
            notes.append("H&W now paid is below the new WD H&W rate.")
            warnings.append(f"{item['occupation_title']}: H&W paid "
                            f"{item['new_hw_paid']:,.2f}/hour is below the new WD H&W rate "
                            f"{item['new_hw_rate']:,.2f}/hour.")
        if actual < 0 or item["new_hw_paid"] < item["prior_hw_paid"]:
            notes.append("A decrease was recorded. FAR 52.222-43(f) requires prompt notice "
                         "of decreases; this worksheet computes increases only.")
        hw_amount = round(hw_increase * hours, 2)
        tax_base = wage_amount + (hw_amount if taxes_on_hw else 0.0)
        tax_amount = round(tax_base * tax_rate_total, 2)
        total = round(wage_amount + hw_amount + tax_amount, 2)
        rows.append({
            "contract_id": item["contract_id"],
            "occupation_code": item["occupation_code"],
            "occupation_title": item["occupation_title"],
            "prior_wd_rate": item["prior_wd_rate"],
            "new_wd_rate": item["new_wd_rate"],
            "prior_rate_paid": item["prior_rate_paid"],
            "new_rate_paid": item["new_rate_paid"],
            "actual_increase_per_hour": round(actual, 4),
            "required_increase_per_hour": round(required, 4),
            "allowable_wage_increase_per_hour": allowed,
            "hours": hours,
            "wage_increase_amount": wage_amount,
            "prior_hw_rate": item["prior_hw_rate"],
            "new_hw_rate": item["new_hw_rate"],
            "prior_hw_paid": item["prior_hw_paid"],
            "new_hw_paid": item["new_hw_paid"],
            "allowable_hw_increase_per_hour": hw_increase,
            "hw_increase_amount": hw_amount,
            "payroll_tax_and_insurance_rate": round(tax_rate_total, 6),
            "payroll_tax_and_insurance_amount": tax_amount,
            "total_adjustment": total,
            "notes": " ".join(notes),
        })
    worksheet = pd.DataFrame(rows)

    deadlines = []
    if frame["wd_received_date"].isna().any():
        warnings.append("At least one row has no wd_received_date; the 30-day deadline "
                        "cannot be computed for it.")
    for received in sorted(d for d in set(frame["wd_received_date"]) if d is not None):
        deadline = received + timedelta(days=notice_days)
        days_left = (deadline - as_of).days
        status = "open" if days_left >= 0 else "passed"
        deadlines.append({"wd_received_date": received, "deadline": deadline,
                          "as_of": as_of, "days_left": days_left, "status": status})
        if status == "passed":
            warnings.append(
                f"The {notice_days}-day notice period for the WD received on {received} "
                f"ended on {deadline} ({-days_left} days before {as_of}). FAR "
                "52.222-43(f) allows the contracting officer to extend the period in "
                "writing; contact the contracting officer before relying on a late notice.")
    total = round(float(worksheet["total_adjustment"].sum()), 2) if not worksheet.empty else 0.0
    return PriceAdjustmentResult(worksheet, deadlines, warnings, total, tax_rate_total)


SUPPORTING_DOCUMENTS = [
    "The prior wage determination incorporated in the contract (number and revision).",
    "The new wage determination incorporated at the anniversary date or option "
    "exercise (number and revision), and the date you received it.",
    "Payroll records for the period before the change showing the rate actually "
    "paid to each employee in each occupation.",
    "Payroll records after the change showing the new rate actually paid.",
    "Records of health and welfare payments (cash or plan contributions) before "
    "and after the change.",
    "The hours basis used for each occupation (staffing plan or recent payroll "
    "hours) and how it was derived.",
    "Your payroll tax and workers' compensation rate notices that support the "
    "rates used for the accompanying taxes and insurance.",
    "This worksheet, showing how each amount was calculated.",
]


def describe_deadline(deadline: dict) -> str:
    days = deadline["days_left"]
    if days > 0:
        return f"open, {days} days left as of {deadline['as_of']}"
    if days == 0:
        return f"open, due today ({deadline['as_of']})"
    return f"passed {-days} days before {deadline['as_of']}"


def render_notice_letter(result: PriceAdjustmentResult) -> str:
    received = ", ".join(str(d["wd_received_date"]) for d in result.deadlines) or "[date received]"
    lines = [
        "# DRAFT - Notice of price adjustment under FAR 52.222-43",
        "",
        "> This is a generic template produced by labor-charge-verifier. It is general "
        "information, not legal or accounting advice. Read your contract and the "
        "current FAR text, and replace every field in square brackets before sending.",
        "",
        "[Date]",
        "",
        "To: [Contracting Officer name], Contracting Officer",
        "[Agency and office]",
        "[Address or email]",
        "",
        "From: [Company legal name], [Address]",
        "",
        "Subject: Contract [contract number] - Notice of price adjustment under FAR "
        "52.222-43, Fair Labor Standards Act and Service Contract Labor Standards - "
        "Price Adjustment (Multiple Year and Option Contracts)",
        "",
        "Dear [Contracting Officer name]:",
        "",
        "In accordance with paragraph (f) of FAR 52.222-43, [Company legal name] gives "
        "notice of a price adjustment claimed under the clause. Wage determination "
        "[new WD number and revision], incorporated on [anniversary or option date], "
        f"was received on {received}.",
        "",
        "The amount claimed is **$"
        + f"{result.total_adjustment:,.2f}"
        + "** for [period, for example the option year from start date to end date], "
        "calculated as follows:",
        "",
        "| Occupation | Allowable wage increase / hour | Hours | Wage increase | "
        "H&W increase | Taxes and insurance | Total |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in result.worksheet.iterrows():
        lines.append(
            f"| {row['occupation_title']} ({row['occupation_code']}) | "
            f"${row['allowable_wage_increase_per_hour']:,.2f} | {row['hours']:,.0f} | "
            f"${row['wage_increase_amount']:,.2f} | ${row['hw_increase_amount']:,.2f} | "
            f"${row['payroll_tax_and_insurance_amount']:,.2f} | "
            f"${row['total_adjustment']:,.2f} |")
    lines += [
        "",
        "Consistent with paragraph (d), the allowable wage and fringe benefit increase "
        "for each occupation is limited to the increase actually paid that was needed "
        "to comply with the new wage determination. Consistent with paragraph (e), the "
        "amount includes the accompanying increases in Social Security and "
        "unemployment taxes and workers' compensation insurance, and does not include "
        "any amount for general and administrative costs, overhead or profit.",
        "",
        "Supporting data, including payroll records, is attached as listed below. "
        "As provided in paragraph (g), the records are available for examination.",
        "",
        "Attachments:",
        "",
    ]
    lines += [f"{n}. {doc}" for n, doc in enumerate(SUPPORTING_DOCUMENTS, 1)]
    lines += [
        "",
        "We will continue performance while this adjustment is pending, as the clause "
        "requires. Please contact [name, title, phone, email] with any questions.",
        "",
        "Sincerely,",
        "",
        "[Name]",
        "[Title]",
        "[Company legal name]",
        "",
    ]
    return "\n".join(lines)

"""Command-line interface: ``lcv``."""

from __future__ import annotations

import argparse
import sys
from datetime import date

from . import __version__
from .common import InputError, load_config
from .invoice_check import check_invoice, load_invoice_data
from .price_adjustment import compute_price_adjustment, describe_deadline, load_price_adjustment_input
from .report import findings_frame, summarize, write_findings_report, write_price_adjustment_outputs
from .wage_check import check_wages, load_wage_data


def _print_summary(findings, paths, billing: bool = True) -> None:
    s = summarize(findings_frame(findings))
    print(f"{s['findings']} findings ({s['high']} high, {s['medium']} medium, {s['low']} low)")
    if billing:
        print(f"  overbilled:      {s['overbilled_count']:>3}  USD {s['overbilled_amount']:>12,.2f}")
        print(f"  underbilled:     {s['underbilled_count']:>3}  USD {s['underbilled_amount']:>12,.2f}")
    print(f"  owed to workers: {s['underpaid_worker_count']:>3}  USD {s['owed_to_workers']:>12,.2f}")
    for kind, path in paths.items():
        print(f"  {kind:<5} {path}")


def cmd_check_invoice(args) -> int:
    config = load_config(args.config)
    findings = check_invoice(load_invoice_data(args.data), config)
    paths = write_findings_report(findings, args.out, "invoice_check",
                                  "Invoice vs. records - findings", args.data)
    _print_summary(findings, paths)
    return 0


def cmd_check_wages(args) -> int:
    config = load_config(args.config)
    findings = check_wages(load_wage_data(args.data), config)
    paths = write_findings_report(findings, args.out, "wage_check",
                                  "Wage-determination compliance - findings", args.data)
    _print_summary(findings, paths, billing=False)
    return 0


def cmd_price_adjustment(args) -> int:
    config = load_config(args.config)
    try:
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
    except ValueError as exc:
        raise InputError(f"--as-of must be a date in YYYY-MM-DD format; got '{args.as_of}'") from exc
    frame = load_price_adjustment_input(args.input, config)
    result = compute_price_adjustment(frame, config, as_of=as_of)
    paths = write_price_adjustment_outputs(result, args.out, args.input)
    print(f"Total adjustment: USD {result.total_adjustment:,.2f}")
    for d in result.deadlines:
        print(f"Notice deadline: {d['deadline']} ({describe_deadline(d)})")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for kind, path in paths.items():
        print(f"  {kind:<9} {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lcv",
        description="Check that labor charges are backed by payroll, timekeeping and "
                    "contract or wage-determination rates. Runs locally; sends nothing.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out", default="reports", help="output folder (default: reports)")
    common.add_argument("--config", default=None,
                        help="settings file (default: config/settings.yaml, then "
                             "config/settings.example.yaml)")

    p = sub.add_parser("check-invoice", parents=[common],
                       help="Module 1: invoice lines vs. roster, timesheets, payroll, prices")
    p.add_argument("--data", required=True, help="folder with the input CSV files")
    p.set_defaults(func=cmd_check_invoice)

    p = sub.add_parser("check-wages", parents=[common],
                       help="Module 2: payroll vs. wage determination")
    p.add_argument("--data", required=True, help="folder with the input CSV files")
    p.set_defaults(func=cmd_check_wages)

    p = sub.add_parser("price-adjustment", parents=[common],
                       help="Module 3: FAR 52.222-43 price-adjustment worksheet")
    p.add_argument("--input", required=True, help="price adjustment input CSV")
    p.add_argument("--as-of", default=None,
                   help="date used for the 30-day deadline check, YYYY-MM-DD (default: today)")
    p.set_defaults(func=cmd_price_adjustment)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

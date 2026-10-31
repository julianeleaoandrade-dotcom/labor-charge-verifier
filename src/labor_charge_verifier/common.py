"""Shared helpers: the Finding record, configuration loading and CSV reading."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .rules import RULES

CONFIG_SEARCH_PATHS = (
    Path("config/settings.yaml"),
    Path("config/settings.example.yaml"),
)


class InputError(Exception):
    """Raised when input files are missing, malformed or not allowed."""


@dataclass
class Finding:
    rule_id: str
    description: str
    employee_id: str = ""
    post_id: str = ""
    line_id: str = ""
    period: str = ""
    billed_amount: float | None = None
    expected_amount: float | None = None
    difference: float | None = None
    direction: str = "none"
    amount_owed_to_worker: float | None = None
    severity: str = field(default="")
    module: str = field(default="")

    def __post_init__(self) -> None:
        rule = RULES[self.rule_id]
        if not self.severity:
            self.severity = rule.severity
        if not self.module:
            self.module = rule.module
        for name in ("billed_amount", "expected_amount", "difference",
                     "amount_owed_to_worker"):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, round(float(value), 2))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rule_title"] = RULES[self.rule_id].title
        return data


FINDING_COLUMNS = [
    "rule_id", "rule_title", "severity", "direction", "module", "employee_id",
    "post_id", "line_id", "period", "billed_amount", "expected_amount",
    "difference", "amount_owed_to_worker", "description",
]


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load the YAML settings file.

    If ``path`` is not given, ``config/settings.yaml`` is used, then
    ``config/settings.example.yaml``, both relative to the current folder.
    Regulatory values are never hard-coded; they must come from this file.
    """
    candidates = [Path(path)] if path else list(CONFIG_SEARCH_PATHS)
    for candidate in candidates:
        if candidate.is_file():
            with candidate.open(encoding="utf-8") as handle:
                config = yaml.safe_load(handle)
            _validate_config(config, candidate)
            return config
    tried = ", ".join(str(c) for c in candidates)
    raise InputError(
        f"No settings file found (looked for: {tried}). Copy "
        "config/settings.example.yaml to config/settings.yaml and review "
        "every value, or pass --config."
    )


REQUIRED_CONFIG_KEYS = {
    "tolerances": ("hours", "money"),
    "workweek": ("start_day",),
    "health_and_welfare": ("rate_per_hour", "weekly_hour_cap", "basis"),
    "overtime": ("weekly_threshold_hours", "multiplier"),
    "payroll_tax_rates": ("social_security", "medicare", "futa", "suta",
                          "workers_compensation"),
    "price_adjustment": ("notice_days", "apply_taxes_to_health_and_welfare",
                         "forbidden_cost_terms"),
}


def _validate_config(config: Any, source: Path) -> None:
    if not isinstance(config, dict):
        raise InputError(f"{source}: the settings file is empty or not a mapping.")
    for section, keys in REQUIRED_CONFIG_KEYS.items():
        if section not in config or not isinstance(config[section], dict):
            raise InputError(f"{source}: missing section '{section}'.")
        for key in keys:
            if key not in config[section]:
                raise InputError(f"{source}: missing '{section}.{key}'.")
            value = config[section][key]
            if isinstance(value, dict) and "value" in value:
                continue
            if isinstance(value, dict):
                raise InputError(f"{source}: '{section}.{key}' needs a 'value'.")


def cfg(config: dict[str, Any], section: str, key: str) -> Any:
    """Return a setting. Settings may be written as plain values or as
    ``value``, ``source`` and ``accessed`` mappings."""
    value = config[section][key]
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def read_csv(path: Path, required: list[str], date_columns: list[str] | None = None,
             comment: str | None = None) -> pd.DataFrame:
    if not path.is_file():
        raise InputError(f"Missing input file: {path}")
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, comment=comment)
    except pd.errors.EmptyDataError as exc:
        raise InputError(f"{path.name}: the file is empty (no header row).") from exc
    except pd.errors.ParserError as exc:
        raise InputError(f"{path.name}: the file is not a valid CSV ({exc}).") from exc
    frame.columns = [c.strip() for c in frame.columns]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise InputError(f"{path.name}: missing columns {missing}")
    for column in frame.columns:
        frame[column] = frame[column].str.strip()
    for column in date_columns or []:
        frame[column] = frame[column].map(lambda v, c=column: _parse_date(v, path.name, c))
    return frame


def _parse_date(value: str, file_name: str, column: str):
    if value == "":
        return None
    try:
        return pd.Timestamp(value).date()
    except (ValueError, TypeError) as exc:
        raise InputError(f"{file_name}: invalid date '{value}' in column '{column}'") from exc


def to_float(frame: pd.DataFrame, columns: list[str], file_name: str,
             rows: pd.Series | None = None) -> pd.DataFrame:
    """Convert columns to numbers. Blank values are an error in the rows
    selected by ``rows`` (all rows by default) and 0 elsewhere."""
    required_rows = rows if rows is not None else pd.Series(True, index=frame.index)
    for column in columns:
        blank = (frame[column] == "") & required_rows
        if blank.any():
            first = int(blank[blank].index[0]) + 2  # +1 header, +1 one-based
            raise InputError(f"{file_name}: blank value in required column '{column}' "
                             f"(first at line {first}).")
        try:
            frame[column] = frame[column].map(lambda v: float(v) if v != "" else 0.0)
        except ValueError as exc:
            raise InputError(f"{file_name}: non-numeric value in column '{column}'") from exc
        frame[column] = frame[column].astype(float)
    return frame


def require_unique(frame: pd.DataFrame, columns: list[str], file_name: str) -> None:
    dup = frame.duplicated(subset=columns, keep=False)
    if dup.any():
        values = frame.loc[dup, columns].drop_duplicates().head(3).to_dict("records")
        raise InputError(f"{file_name}: {columns} must be unique; repeated: {values}")


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def week_start_index(config: dict[str, Any]) -> int:
    name = str(cfg(config, "workweek", "start_day")).strip().capitalize()
    if name not in WEEKDAYS:
        raise InputError(f"workweek.start_day must be one of {WEEKDAYS}; got '{name}'")
    return WEEKDAYS.index(name)


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    return f"{count} {singular if count == 1 else (plural_form or singular + 's')}"

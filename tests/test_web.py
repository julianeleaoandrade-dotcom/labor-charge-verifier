"""Checks that keep the browser version in step with the package."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_web_module_list_matches_package():
    app = (ROOT / "web" / "app.js").read_text()
    block = re.search(r"PACKAGE_MODULES = \[(.*?)\];", app, re.S).group(1)
    listed = set(re.findall(r'"([a-z_]+)"', block))
    actual = {p.stem for p in (ROOT / "src" / "labor_charge_verifier").glob("*.py")}
    assert listed == actual


def test_templates_have_the_same_headers_as_the_sample_data():
    for template in (ROOT / "templates").glob("*.csv"):
        header = [l for l in template.read_text().splitlines() if not l.startswith("#")][0]
        sample = template.name if template.name != "wage_determination.csv" \
            else "wage_determination_SAMPLE.csv"
        sample_header = [l for l in (ROOT / "sample-data" / sample).read_text().splitlines()
                         if not l.startswith("#")][0]
        assert header == sample_header, template.name


def test_site_builds(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts" / "build_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = tmp_path / "site"
    module.build(out, wheels=False)
    for path in ["index.html", "app.js", "runner.py", "config/settings.example.yaml",
                 "py/labor_charge_verifier/invoice_check.py", "sample-data/invoice.csv",
                 "templates/invoice.csv", "templates/labor-charge-verifier-template.xlsx",
                 "sample-data/sample-workbook.xlsx", "wheels/manifest.json"]:
        assert (out / path).is_file(), path


def test_runner_works_with_the_package(tmp_path, monkeypatch, sample_dir):
    """Run the browser glue in plain Python against the sample data."""
    import json
    import sys
    sys.path.insert(0, str(ROOT / "web"))
    import runner
    monkeypatch.setattr(runner, "CONFIG_PATH", ROOT / "config" / "settings.example.yaml")
    invoice = json.loads(runner.run_invoice(str(sample_dir), "{}"))
    assert invoice["ok"] and invoice["summary"]["findings"] == 14
    wages = json.loads(runner.run_wages(str(sample_dir), json.dumps({"hw_rate": "5.55"})))
    assert wages["ok"] and wages["summary"]["owed_to_workers"] == 217.60
    price = json.loads(runner.run_price(str(sample_dir / "price_adjustment_input.csv"),
                                        "{}", "2026-10-01"))
    assert price["ok"] and price["summary"]["total_adjustment"] == 27358.40
    book = json.loads(runner.convert_workbook(str(sample_dir / "sample-workbook.xlsx")))
    assert book["ok"] and book["sheet_names"]["invoice.csv"] == "Invoice"
    bad = json.loads(runner.run_wages(str(tmp_path), "{}"))
    assert bad["ok"] is False and "Missing input file" in bad["error"]

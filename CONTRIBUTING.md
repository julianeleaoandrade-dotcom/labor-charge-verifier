# Contributing

Thank you for helping improve labor-charge-verifier.

## Reporting a problem

Open an issue with:

- what you ran (command and version: `lcv --version`);
- what you expected and what happened;
- a **small, fictitious** example that reproduces it.

Never attach real payroll, timesheets, invoices, names or Social Security
numbers.

## Proposing a rule or a change

- Each rule needs an ID, a plain description of what it checks, why it
  matters and a public source (statute, regulation or contract clause). Add it
  to `src/labor_charge_verifier/rules.py` and `docs/rules-catalog.md`.
- Values that change over time belong in `config/settings.example.yaml`, with
  their source and access date, never in code.
- Add tests. If you change the sample data, update
  `sample-data/EXPECTED_FINDINGS.md` and the tests that check it.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The browser version lives in `web/`. To try it locally, build the site and
serve it:

```bash
python scripts/build_site.py _site
python -m http.server 8000 --directory _site
```

Then open <http://localhost:8000>. If you add a module to
`src/labor_charge_verifier/`, add it to `PACKAGE_MODULES` in `web/app.js`
(a test checks this).

Keep the language of documentation and messages plain and factual.

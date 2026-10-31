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

Keep the language of documentation and messages plain and factual.

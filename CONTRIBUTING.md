# Contributing

Contributions should strengthen falsifiability, reproducibility, or safety.

Before proposing a change:

```bash
python3 -m unittest discover -s tests
python3 scripts/validate_experiment_records.py .
python3 scripts/validate_experiment_index.py .
python3 scripts/validate_expert_manifest.py templates/expert-package.json
python3 scripts/check_public_safety.py .
```

Experiment reports must use the template, declare failure criteria in advance, and avoid
claims broader than the tested configuration.

New experiment reports declare `Schema: strict-v1`. The validator checks their required
metadata and sections, including rejection of empty bodies and known template placeholders;
historical reports without a schema declaration remain legacy records.

Required metadata values are parsed from their own line. Empty values are invalid, and the
unchanged template `Data` value plus the exact short markers declared by the validator are
rejected as structural placeholders rather than semantic-quality judgments.

Every `EXP-NNN` file must occur exactly once in the experiment index. Indexed status and
verdict values must match the corresponding record. The indexed title must match the record
heading; a backslash-escaped table pipe is compared with its rendered literal pipe.

Expert packages start from `templates/expert-package.json` and remain in quarantine. The
structural validator requires explicit scope exclusions, provenance, separated knowledge,
experience, skill, tool, and adapter layers, target and held-out regression tests, expiry, and
an unload rollback. Validation does not constitute promotion or evidence of runtime safety.

Never submit private infrastructure details, secrets, raw logs, private datasets, model
weights, or identifying system metadata. Report resources using the anonymous capability
envelope.

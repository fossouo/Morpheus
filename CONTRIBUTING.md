# Contributing

Contributions should strengthen falsifiability, reproducibility, or safety.

Before proposing a change:

```bash
python3 -m unittest discover -s tests
python3 scripts/validate_experiment_records.py .
python3 scripts/check_public_safety.py .
```

Experiment reports must use the template, declare failure criteria in advance, and avoid
claims broader than the tested configuration.

New experiment reports declare `Schema: strict-v1`. The validator checks their required
metadata and sections; historical reports without a schema declaration remain legacy records.

Never submit private infrastructure details, secrets, raw logs, private datasets, model
weights, or identifying system metadata. Report resources using the anonymous capability
envelope.

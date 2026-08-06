# Experiments

Every experiment uses [`templates/experiment.md`](../templates/experiment.md).

| ID | Title | Status | Verdict |
|---|---|---|---|
| EXP-000 | Research map and falsifiable claims | complete | proceed |
| EXP-001 | Public-safety boundary checker | complete | pass |
| EXP-002 | Held-out promotion gate | complete | pass |
| EXP-003 | Machine-checkable experiment record | complete | pass |
| EXP-004 | Section-body validation | complete | pass |
| EXP-005 | Metadata-value validation | complete | fail |
| EXP-006 | Line-bounded metadata validation | complete | pass |
| EXP-007 | Experiment-index consistency | complete | pass |
| EXP-008 | Experiment-title consistency | complete | pass |

Status values: `planned`, `running`, `complete`, `blocked`, `superseded`.

Verdict values: `pass`, `fail`, `mixed`, `inconclusive`, `proceed`, `stop`.

New records use the opt-in `strict-v1` contract in the experiment template and are checked by
`python3 scripts/validate_experiment_records.py .`. Records created before the contract remain
legacy documents rather than being retroactively described as preregistered.

The index is checked by `python3 scripts/validate_experiment_index.py .`. Every experiment file
must appear exactly once, and its indexed status and verdict must match the record.

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
| EXP-009 | Expert-package manifest contract | complete | pass |
| EXP-010 | Pinned reference-date expiry gate | complete | pass |
| EXP-011 | Cross-layer identifier uniqueness | complete | pass |
| EXP-012 | Loadable non-parametric recall | complete | pass |
| EXP-013 | Transactional expert composition | complete | pass |
| EXP-014 | Package-qualified expert routing | complete | pass |

Status values: `planned`, `running`, `complete`, `blocked`, `superseded`.

Verdict values: `pass`, `fail`, `mixed`, `inconclusive`, `proceed`, `stop`.

New records use the opt-in `strict-v1` contract in the experiment template and are checked by
`python3 scripts/validate_experiment_records.py .`. Records created before the contract remain
legacy documents rather than being retroactively described as preregistered.

The index is checked by `python3 scripts/validate_experiment_index.py .`. Every experiment file
must appear exactly once, and its indexed status and verdict must match the record.

## Bounded capability checkpoint

The three successful experiments beginning with EXP-012 form a bounded checkpoint. At least one
must show a new or improved behavior on held-out cases with a baseline and measured gap; schema,
validator, contract, refactor, and test-count changes do not qualify alone. After the third
successful run, compare all three experiments. If none establishes a capability gain, recommend
pausing the daily loop or moving it to a weekly cadence without claiming progress.

The EXP-012 through EXP-014 checkpoint is complete. All three experiments passed their narrow
synthetic protocols: loadable exact recall, transactional expert composition, and explicit
package-qualified routing each improved held-out target accuracy from zero to perfect with no
drop on their locked regression cases. EXP-012 satisfies the required behavioral-gain criterion;
the comparison is reported in EXP-014. This supports continuing only toward harder held-out
behavioral questions and does not establish general capability or self-improvement.

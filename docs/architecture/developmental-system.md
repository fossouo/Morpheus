# Developmental system hypothesis

## Components

### Cognitive kernel

A stable model responsible for language, task decomposition, uncertainty expression,
tool selection, and general reasoning. It is not expected to store all current facts.

### Morphology controller

Selects an execution phenotype from the capability envelope: model slice, precision,
depth, resident experts, offload policy, and task placement.

### Expert foundry

Builds versioned expert packages from a need, evidence, procedures, and tests. New
packages begin in quarantine.

### Memory system

Maintains separate factual, episodic, and procedural stores. Claims retain provenance,
time, confidence, and contradiction links.

### Skill library

Stores executable, testable procedures. Skills are composed at run time and may be
retired independently of the cognitive kernel.

### Latent world model

Predicts state transitions relevant to planning. It need not reconstruct every input
token or pixel.

### Evaluation governor

Controls promotion and rollback using held-out tests, cost budgets, source-quality
checks, and regression limits.

## Expert package contract

An expert package should eventually contain:

- domain scope and exclusions;
- ontology and query vocabulary;
- evidence graph with primary-source provenance;
- retrieval and memory configuration;
- tools and executable skills;
- evaluation fixtures and acceptance thresholds;
- expiry and refresh policy;
- permissions and resource budget;
- optional parametric adapter;
- compatible anonymous capability classes.

The package is the unit of specialization. A neural expert is only one optional field.

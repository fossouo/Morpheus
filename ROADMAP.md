# Roadmap

The roadmap is intentionally incremental. Each phase must produce evidence before the
next one receives additional compute or autonomy.

## Phase 0 — Measurement contract

- Define the public/private boundary.
- Define anonymous compute capability classes.
- Create schemas for experiments and expert packages.
- Establish baseline tasks, costs, and quality metrics.
- Build deterministic synthetic fixtures.

Exit condition: the repository can reject unsafe publications and validate experiment
records automatically.

## Phase 1 — Non-parametric development

- Compare static RAG with structured factual and episodic memory.
- Add claim-level provenance and contradiction tracking.
- Build reusable procedural skills without changing base weights.
- Measure capability gained per stored byte and per inference unit.

Exit condition: at least one task improves over the fixed-kernel baseline without
fine-tuning, while retaining provenance and passing regression tests.

## Phase 2 — Expert packages

- Define an expert package containing scope, sources, memory, tools, tests, expiry, and
  optional adapters.
- Test expert discovery, composition, conflict resolution, quarantine, and rollback.
- Measure expert load cost and interference with unrelated tasks.

Exit condition: a newly assembled expert improves its target task and does not exceed the
predeclared regression budget.

## Phase 3 — Morphology

- Select precision, depth, expert residency, and placement from capability constraints.
- Compare static profiles with an adaptive policy.
- Measure quality, latency, memory, energy proxy, and reconfiguration overhead.

Exit condition: one adaptive policy dominates or matches fixed profiles across at least
three anonymous capability classes.

## Phase 4 — Latent prediction

- Test whether latent-state prediction improves planning or data efficiency.
- Keep the language model as interface and symbolic tool rather than sole state model.
- Compare token-only, retrieval-augmented, and latent-predictive variants.

Exit condition: a latent component produces a measurable planning or sample-efficiency
gain that survives held-out evaluation.

## Phase 5 — Guarded self-improvement

- Allow the system to propose changes to memory, retrieval, skills, and expert manifests.
- Evaluate each change in quarantine.
- Promote only changes that pass held-out tests; automatically revert regressions.

Exit condition: repeated improvement cycles produce positive transfer without safety or
quality drift.

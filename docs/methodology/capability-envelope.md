# Anonymous capability envelope

Public reports describe resources by capability, never by private machine identity or
network placement.

## Compute classes

| Class | Public meaning |
|---|---|
| C0 | CPU-only or equivalent low-acceleration execution |
| C1 | Constrained accelerator; small quantized models and lightweight experts |
| C2 | Mid-range accelerator; medium quantized models or several small resident modules |
| C3 | High-capacity local accelerator; larger sparse or multimodal experiments |
| CM | Multiple heterogeneous workers coordinated at task level |

These labels do not imply a specific vendor, product, host count, memory size, or topology.

## Runtime feature vector

An experiment may publish the following normalized or bucketed properties:

- `memory_class`: low, medium, high;
- `compute_class`: C0, C1, C2, C3, or CM;
- `precision_family`: integer-low-bit, float-low-bit, half, or mixed;
- `runtime_family`: generic tensor runtime, generic graph runtime, or generic model server;
- `interconnect_class`: local, fast, constrained, or not-applicable;
- `load_state`: idle, shared, or saturated;
- `measurement_confidence`: measured, estimated, or unknown.

Exact hardware identifiers, addresses, paths, ports, process lists, command histories,
device UUIDs, and raw monitoring output are forbidden.

## Publication transform

Before publication:

1. map private observations to the envelope;
2. remove unique or identifying fields;
3. aggregate repeated measurements;
4. retain only metrics needed to test the hypothesis;
5. run `python3 scripts/check_public_safety.py .`;
6. manually review the staged diff when an experiment used local infrastructure.

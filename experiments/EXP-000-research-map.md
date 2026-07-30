# EXP-000 — Research map and falsifiable claims

- **Date**: 2026-07-30
- **Status**: complete
- **Compute**: none
- **Data**: published primary sources

## Question

Do published results support the individual components of a developmental,
infrastructure-adaptive language system?

## Findings

| Axis | Representative evidence | Supported claim | Remaining gap |
|---|---|---|---|
| Elastic morphology | [MatFormer](https://arxiv.org/abs/2310.07707), [Flextron](https://arxiv.org/abs/2406.10260), [Any-Precision LLM](https://arxiv.org/abs/2402.10517) | One trained system can expose multiple sizes, paths, or precisions. | Fully autonomous morphology across arbitrary hardware is not demonstrated. |
| Fine experts | [DeepSeekMoE](https://arxiv.org/abs/2401.06066), [PEER](https://arxiv.org/abs/2407.04153), [Kimi K3](https://arxiv.org/abs/2607.24653) | Fine-grained sparse routing improves the capacity/compute trade-off. | Experts remain trained tensors rather than autonomous knowledge packages. |
| External memory | [RETRO](https://arxiv.org/abs/2112.04426), [Memorizing Transformers](https://arxiv.org/abs/2203.08913), [HippoRAG 2](https://arxiv.org/abs/2502.14802) | Knowledge and experience can be added without putting everything in base weights. | Deep reasoning over large non-parametric memory remains unreliable. |
| Evolving memory | [EvolveMem](https://arxiv.org/abs/2605.13941), [AdaMEM](https://arxiv.org/abs/2606.05684) | Memory contents and retrieval policies can adapt after deployment. | Open-world stability and contamination resistance are unresolved. |
| Skills and tools | [Voyager](https://arxiv.org/abs/2305.16291), [Toolformer](https://arxiv.org/abs/2302.04761) | Agents can acquire reusable skills or tool-use policies. | Results remain domain- or tool-constrained. |
| Scientific research | [PaperQA2](https://arxiv.org/abs/2409.13740), [OpenScholar](https://arxiv.org/abs/2411.14199), [SAFE](https://arxiv.org/abs/2403.18802) | Search, synthesis, contradiction detection, and claim checking can outperform basic RAG. | Autonomous source trust remains fallible. |
| Latent world models | [DreamerV3](https://www.nature.com/articles/s41586-025-08744-2), [V-JEPA 2](https://arxiv.org/abs/2506.09985), [LeWorldModel](https://arxiv.org/abs/2603.19312) | Useful prediction and planning can happen in latent state space. | General abstract world modeling beyond control and perception is immature. |
| Guarded improvement | [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | Agent software can improve through variation and empirical selection. | General and safe recursive self-improvement is not demonstrated. |

## Falsifiable program claims

1. Structured external memory will outperform static vector retrieval at equal inference
   budget on associative and contradiction-sensitive tasks.
2. A versioned skill library will improve task completion without changing kernel weights.
3. Expert packages will reduce domain-error rate without exceeding a fixed regression
   budget on unrelated tasks.
4. A morphology policy will match or dominate fixed profiles across at least three
   anonymous compute classes.
5. Guarded change proposals will improve held-out performance more often than an
   unguided mutation baseline.

## Verdict

**Proceed.** Each component has prior evidence, while their governed integration remains
an open research contribution.

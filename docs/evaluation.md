# Evaluation and practical limits

[← Documentation](README.md) · [Architecture](architecture.md) · [Live acceptance](insured-vibe-coding/test-plans/live-liara.md)

## Evidence at a glance

| Layer | Recorded result | Source and qualification |
|---|---|---|
| Backend and frontend | Current reviewed suites pass; exact source/check counts are owned by the implementation checkpoint | [Implementation progress](implementation-progress.md); recorded results, not a fresh CI claim |
| Independent actual UI | 29/29 rendered scenarios | [UI ledger](insured-vibe-coding/test-plans/operator-ui.md), [raw evidence](qa-evidence/operator-ui.json) |
| Genuine model evaluation | 8/8 expected cause-family or abstention outcomes over 11 model calls | [diagnosis.json](../results/diagnosis.json); synthetic diagnostic inputs, not live incident success |
| Observation baselines | Same cases inspected using restricted HTTP-only and latest-release-only views | [observation-baselines.json](../results/observation-baselines.json); different output contracts |
| Packaged services | Healthy → actual dependency failure → restored expected build | [Container evidence](qa-evidence/packaged-containers.json); local constrained containers |
| Corrected runtime image | Genuine schema/cleanup proof | [Runtime evidence](qa-evidence/public-runtime-image.json); separate from the earlier eight-case run |
| Actual provider workflow | LIVE1–LIVE5 passed on two exact disposable cloud targets | [Live ledger](insured-vibe-coding/test-plans/live-liara.md); actual source/expiry/replacement/recovery proof, not fixtures |
| Local diagnostic breadth | Actual loopback delay/fast503 and genuine Codex; initial busy failure retained, fresh timeout result completed | [Bounded report](qa-evidence/local-diagnostic-breadth/REPORT.md), [manifest](qa-evidence/local-diagnostic-breadth/manifest.json); provider metadata fixtures, no cloud slowdown/capacity claim |
| Public narrated demo |304.92s actual evidence, anonymous decode/play/seek/mobile pass | [Demo page](https://milad-afkhami.github.io/starcoach-liara-operator/), [public retest](qa-evidence/liara-demo-public-retest.json); synthetic voice and edits disclosed |

The latest Persian interface, stable-owner history and bounded recent-log excerpt corrections have a separate [blind review record](review-feedback.md); the original diagnostic fixture run remains identified below.

## Diagnostic outcomes

[diagnosis.json](../results/diagnosis.json) records an actual isolated Codex run over eight separately labelled synthetic cases, with expected answers retained by the evaluator. All eight met their expected cause-family or abstention outcome. Eleven model calls took roughly 10–22 seconds per case on the inspected local runtime. The investigator has no write interface, and no application write occurred in that evaluation. These observations do not establish real-incident success, strategy optimality, production MTTR improvement or a different model’s accuracy.

| Case | Expected useful behavior |
|---|---|
| Dependency response mismatch | Identify contract evidence and retain unresolved target/repair questions |
| Process crash | Ground the failure family in actual evidence |
| Dependency timeout | Distinguish a slow boundary from a schema mismatch |
| Distracting unrelated deployment | Do not turn recency into causality |
| Observer authentication failure | No application change when the problem is access |
| Stale logs | Respect evidence age |
| Unknown metric units | Avoid invented capacity percentages |
| Insufficient evidence | Explicitly abstain or request a useful next observation |

These are deliberately designed diagnostic cases, not random production incidents. Truth is in the separate harness fixture and never sent as a scenario/expected-answer label in model evidence. Output schemas constrain read/action names and citations; independent code rejects stale generations, unsupported IDs and unenrolled repair actions.

## Baselines and interpretation

[observation-baselines.json](../results/observation-baselines.json) examines the same inputs through HTTP-only and latest-release-only observation baselines. HTTP-only reports available endpoint status; release-only reports whether a fresh release payload exists. Neither supports a causal claim by itself. These deliberately restricted baselines have different output contracts, so we do not manufacture a comparative cause-accuracy percentage or claim to outperform an existing SRE product. The unrelated-release case is a useful example of why visible change needs discriminating evidence.

## Real local services and rendered acceptance

The actual local two-service and packaged-container runs exercise a genuine HTTP dependency contract, process liveness, 502 regression, build propagation, correlated logs and restored healthy source. Independent rendered QA includes real model work, cancellation, same-failure observation stability, material invalidation, multi-session isolation, watch stop/expiry, active-call restart, provider-access gaps and missing model configuration. See [the precise local ledger](insured-vibe-coding/test-plans/operator-ui.md) and [container evidence](qa-evidence/packaged-containers.json).

## Actual cloud acceptance and remaining limits

The actual account-specific inventory/log/release/history/metric reads, two cloud baselines, independent approved fault, exact source redeployment and three-round original-symptom/build recovery are recorded in [LIVE1–LIVE5](insured-vibe-coding/test-plans/live-liara.md). An unused approval expired naturally and returned409; a fresh exact replacement completed a normal three-round/six-probe verification. Earlier inconclusive/invalid-output/cautious results remain retained rather than relabelled as success.

The separate local breadth run measured a dependency baseline around19ms, induced delay around1.8s with gateway timeout around0.84s, and a fast upstream503. Real local HTTP is combined with explicitly labelled provider metadata fixtures. It does not prove a cloud capacity incident. The initial diagnosis failed at shared-gate contention; the reviewed fix waits only on pre-start busy, with cancellation and the same original deadline. A fresh actual run retained unknown CPU/RAM/capacity and requested no application change. No ledger reset or completed-call replay occurred.

Known limits include the24-hour/200-event fallback for recent network-runtime serving identity, unenrolled targets remaining read-only, known-good source repair rather than broad configuration operations, observer clock uncertainty, local model-worker availability and a small designed evaluation set. [API capability qualifications](api-capabilities.md) and [deployment/lifecycle scope](deployment.md) explain them. Final team identity and one-time contest submission remain open in the submission record.

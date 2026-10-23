# Liara usability revision R2

Owner: usability/r2-liara. Source: original Liara challenge and canonical planning/liara-plan.md, constrained by AGENTS.md. Backend change is limited to versioned user-facing model writing guidance and fixed checklist/setup-advice prose; schema/provider/approval/evidence-storage/model-budget contracts stay unchanged. Existing consequential flows remain reachable. Root owns independent review, publication and live operator refresh.

## Design

Audience: Persian-speaking vibe coders who need to know what broke and what to ask their coding agent to fix. The first screen answers current checks, diagnosis, impact and next action. Use natural Persian with familiar log, deploy and release terminology. Provider Running is separate from a failing HTTP check; absence is unknown.

Palette: canvas #edf3f8, surface #ffffff, ink #153b49, action #14698a, failure #b64237, success #2f7764. Keep bundled Vazirmatn and LTR technical islands. Compact service navigation and a contextual service workspace replace the notebook metaphor. Overview, Resources, Logs/evidence and Changes are explicit views; actions and recovery stay on overview. No decorative hero or repeated card grid. Alignment follows RTL; numbers and source identifiers remain unchanged.

Layout: service rail | service header / view navigation / selected context. Overview: HTTP status strip → ask or completed diagnosis → impact/next step → copy/download Codex handoff → exact action/recovery → bounded watch. Evidence: readable per-kind facts first, raw sanitized JSON only in closed advanced details. Resources: native timestamps on SVG charts, separate CPU/RAM and applet identities, no replica sum, invalid/future/older-than-window samples excluded, explicit breaks for missing/invalid points or >60-second gaps. Unknown-unit evidence never becomes a percentage. No load/capacity conclusion.

Review against brief: existing scientific provenance was occupying the primary interaction; move it into audit disclosure while retaining exact approval hashes before approval. This is a service workbench rather than a long report. Code-agent handoff has English instructions with the original Persian diagnosis/unknowns quoted unchanged. It is a text artifact generated deterministically from the current frozen diagnosis and cited evidence; it requests repository investigation, a minimal fix and regression tests, distinguishes unknowns and never grants deploy authority or invents repo paths.

## Implementation and verification

1. Add RED behavior tests for chart validation/segmentation, readable evidence summaries and scoped handoff (unknowns, contradictory evidence, historical result, no guessed paths or raw secrets). Implement pure presentation helpers and typed chart data. Run frontend behavior suite.
2. Build resource SVG charts and a copy/download handoff component; reframe evidence dialog, navigation and diagnosis/impact/next step. Keep operation API calls and disabled-state guards unchanged. Update canonical browser journeys to navigate intentional views/disclosures only.
3. Run canonical backend pytest, Ruff, frontend behavior/build and all canonical browser tests on owned isolated fixture ports/state with deterministic model only. Execute written usability QA and inspect desktop/mobile screenshots. Independent reviewer receives plan, diff, source and evidence. No commits/pushes/cloud/model calls/live restarts.

## Review focus

Do tabs hide errors or pending operations? Do expired sessions clear all newly added private UI? Can a download contain unrelated or post-cutoff evidence? Can raw values leak onto a chart despite bad quality/units? Do disconnected points look continuous? Are exact target/release/artifact/policy/digest and expiry reviewable before approval? Does recovery still outrank historical diagnosis? Preserve previous no-endpoint and observer-only flows.

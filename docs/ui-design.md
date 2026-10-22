# Interface direction — Service Watch

A service-first incident notebook for a Liara customer. The first question is which deployed service needs attention, what is actually observed, and whether the observer can see enough to diagnose it. No healthy baseline, source upload or checkout contract is required for browsing services or starting an investigation.

Use a light paper surface, dark navy text, blue selected-service controls, orange incident emphasis, and quiet green only for checks that actually pass. Use locally bundled system/Inter-style sans typography; avoid a generic chatbot dashboard and decorative metric tiles. The meaningful contrast is a green process-health response beside a failing configured endpoint, followed by the specific evidence that explains the difference.

Desktop: compact header with selected team/provider mode, a service list, and a wide detail/incident notebook. Mobile: list then detail with direct navigation. The top persistent fixture banner must say provider metadata is simulated while local HTTP checks and Codex calls are real. Live mode never silently falls back to fixtures. Unknown resource units are shown as an evidence gap, not a zero or percentage.

Main actions: select service, refresh observations, ask a plain-language question, investigate, inspect cited evidence, start/stop a15-minute watch. Observation/model loading states and cancellation are explicit. A change timeline separates release timing from cause. Evidence dialogs show source/kind/quality/observation and availability times, bounded content and truncation. No source credential, password or controller scenario label appears in the notebook.

A repair card exists only for an explicitly enrolled verified artifact on a supported target. It shows exact target/current release/artifact/policy/expiry, then separate Approve and Execute controls. Provider readiness and fresh original-symptom/build verification are distinct stages. A failed/inconclusive verification leaves the issue open; stopping periodic watch does not hide a submitted operation. Initial app setup is an owner-only CLI, outside the investigator tools.

Native dialogs provide keyboard containment and Escape/focus return. Do not block access to browser chrome. Use visible focus, readable12–16px evidence labels, minimum44px primary controls, and no horizontal overflow at390×844. Actual user flows must drive controls; API tests alone do not establish UI usability.

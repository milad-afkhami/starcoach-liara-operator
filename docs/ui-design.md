# Persian customer interface

The audience is a Persian-speaking Liara customer investigating deployed services. Persian is the default document and product language; no extra English mode is required to complete the core flow.

| Decision | Contract |
|---|---|
| Typography | Locally bundled Vazirmatn, covered by its bundled OFL license; fontTools inspection confirms GSUB `ss01` exists. `font-feature-settings: "ss01"` shapes ordinary UI digits without mutating data. |
| Technical data | Service names, paths, hashes, password input and source JSON are isolated LTR; source values keep Latin digits and keys. |
| Palette | Ink `#153b49`, action blue `#14698a`, evidence teal `#2f7764`, failure red `#b64237`, canvas `#f3f7fa`, line `#d7e3e8`. This is an independent Liara-oriented interface, not a claim to reproduce an official Liara design kit. |
| Hierarchy | Service navigation includes a first-viewport «پرسیدن از دستیار» action that focuses the question. Observed facts → investigation → exact action → bounded monitoring remain the evidence flow. A failure badge never hides successful liveness evidence. |
| Direction | Document `lang=fa`, `dir=rtl`; sidebar, arrows, timeline spacing and form reading order follow RTL. |
| Focus | Visible two-pixel focus ring on actionable controls. Compound search has one group focus treatment; no double input border. |
| Responsive layout | Existing service dashboard uses available desktop space; mobile stacks navigation and evidence, retaining all operational controls. |
| Honesty | Local fixture banner, missing evidence, unknown diagnosis and unregistered repair remain explicit in Persian. No cloud capability is fabricated by translating the interface. |

API states and error codes stay unchanged. Persian labels are presentation only. Model prose is requested in Persian at the backend boundary; cited raw evidence is never translated or rewritten.

The single configured owner has durable history across browser logins. Browser sessions remain separately revocable; signing out clears all private UI state. Identity derives from the operator instance secret, so this is explicitly a single-owner interface, not a multi-user account system. Existing records written under the earlier session-as-owner bug are not silently reassigned.

After verified recovery, the final result and verification end time precede a collapsed, clearly labelled pre-action diagnosis with its evidence cutoff. Opening it retains original model prose and citations unchanged; outcome/unknown labels refer to the analysis time. Submitted operations also retain that pre-action context while the analysis stays expanded. Release IDs are labelled pre-deployment versus submitted, and only completed/recovered operations call the latter deployed-and-verified. Exact approval hashes remain available.

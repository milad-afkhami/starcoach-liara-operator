# Actual deployment preparation and approval

[← Documentation](README.md) · [User guide](user-guide.md) · [Getting started](getting-started.md)

The exact disposable cloud resources below were provisioned23October2026 using the existing Nova Prime contest credit. Both services passed real baseline/build verification. An independent approved fault, genuine diagnosis, exact source redeployment and three-round recovery are recorded; the final-build unused-approval expiry, fresh exact replacement and normal three-round recovery also passed. Local fixture acceptance is still separate from [actual LIVE1–LIVE5](insured-vibe-coding/test-plans/live-liara.md).

| Resource | Actual role | URL |
|---|---|---|
| `liara-watch-delivery-2026` | Dependency with enrolled known-good source | https://liara-watch-delivery-2026.liara.run |
| `liara-watch-storefront-2026` | Monitored service with original failure check | https://liara-watch-storefront-2026.liara.run |
| Local operator | Private owner UI and isolated Codex; no model authentication on Liara | `http://127.0.0.1:8662` in the demonstrated environment |

The scenario deliberately changes between healthy and faulty states; the URLs are not promises of continuous production availability. The isolated network is `starcoach-contest-2026`. The API token expires after seven days and is account-level; team/target scope is enforced by the application, not claimed as a provider-native key permission. No personal top-up, plan upgrade or unrelated existing application was changed.

## Reviewed resource scope and quote

Use Nova Prime’s selected infrastructure team with two new Docker apps: `liara-watch-delivery-2026` and `liara-watch-storefront-2026`. Each starts with one Earth/base plan,0.5GBRAM/0.5 CPU/5GBincluded disk, basic feature bundle, port8000. They are stateless demo services. The operator and private Codex authentication remain local; no hosted operator or Docker-socket mount is proposed.

The signed-in final creation review inspected22October2026 showed475,000toman/month base plus275,000feature bundle plus75,000VAT:825,000/month, rounded to1,146toman/hour including10% VAT. Two apps for48hours are110,016toman at that hourly quote. The separate Torob app would add55,008toman over48hours, for165,024combined, before any separately quoted disk/network/other charges. The console credit observation was2,000,000toman. Quotes are not incurred charges or a promise of credit treatment. Current catalogue and final checkout must still match before provisioning.

Official CLI creation sends `planID`, `bundlePlanID`, `network`, `platform` and `readOnlyRootFilesystem`. Public OpenAPI omits the feature-bundle field. Basic is the bundle ID, not the plan ID; discover actual available plan IDs from authenticated `/v1/me`. The account’s `/v1/networks` must contain the explicitly selected network. An absent network is a real setup prerequisite; do not omit the field or invent a network-creation API. The new isolated contest network and expiring account token were provisioned within the reviewed disposable-resource scope. The actual API console inspected22October exposes expiry choices, not resource/team permission scopes; the Create new key button immediately performs the token POST. Do not call this a provider-enforced team-scoped key. The application independently enforces the selected team/registered targets. A 7-day token covers the remaining contest/judging window; the1-day option generated now would expire before the contest cutoff. That earlier console observation was read-only; the subsequently provisioned expiring token is private and is excluded from source and model evidence.

Sources: [API authentication/team scope](https://docs.liara.ir/references/api/about/), [published PaaS specification](https://developers.liara.ir/spec/paas.yaml), [official CLI at inspected commit](https://github.com/liara-cloud/cli/tree/14ec35f79d703a09a5e3abbb22ba59239cdde80d), [Docker deployment](https://docs.liara.ir/paas/docker/how-tos/deploy-app/). Final console review is account-specific, not a public rate guarantee.

## Owner workflow

Generate a separate private live environment with `scripts/init_operator.py --mode live --team <verified-team-id> --env-file <private-live-env> --access-file <private-access-file>` and the three optional explicit Codex parameters. Add the owner-provisioned `LIARA_API_TOKEN` privately; never pass it in a command argument or commit it. The generated live registry path is `data/live-setup/registry.json`. Do not overwrite the local fixture environment.

Run `uv run --env-file <private-live-env> python scripts/owner_setup.py inspect` to read the account catalogue, network IDs and inventory. It does not return unrelated account profile fields or bearer secrets. Confirm the chosen team/network and current quote. Use `propose-create --app <exact-demo-name> --network <existing-scoped-network-id>`. This prints a five-minute proposal ID/digest; `approve-execute --id <id> --digest <digest>` approves and executes only that exact proposal. No blanket yes flag exists. A fresh preflight rejects name collision, wrong network or changed price.

Create delivery first. After exact create completion, `package --app liara-watch-delivery-2026` creates an allowlisted archive/manifest and enrolls its exact approved source hash. `propose-initial --app liara-watch-delivery-2026` requires an app created in this setup ledger and no existing release. Inspect and approve its exact digest. Use `status --id <deployment-operation-id>` at ten-second intervals for bounded reconciliation. When ready, `baseline --id <deployment-operation-id>` must observe the new serving release/build and three fresh passing requests before registering known-good. Packaging alone does not register a baseline.

Repeat creation/package/initial deployment/baseline for storefront. Its archive contains the fixed public delivery origin as a nonsecret config file. Then `enable-repair` rechecks both actual baselines and writes the source/policy/dependency registry. Restart the local live operator to load this registry. Existing other services are still read-only. Never register an old arbitrary app merely because its name matches; the setup ledger must prove creation.

## Independent fault and recovery

Only after both baselines pass, `uv run --env-file <private-live-env> python harness/live_fault.py propose` packages the incompatible dependency separately. It never enters the operator’s known-good map. Inspect its exact target/before-release/archive hash, then explicitly approve with `approve-execute --id <id> --sha256 <hash>`. A single-use controller claim and frozen bytes protect the write. `status` only reconciles known source/release identity; it never repeats a POST. Unknown upload identity remains unknown.

Observe the real storefront502/liveness200 in the UI, start a bounded watch or manual investigation, inspect cited evidence and request a repair proposal. Approve the exact operation digest, execute once, and retain results. The UI must remain inconclusive if release readiness, serving identity, build or original endpoint proof is missing. Run the separate observer-access negative case without changing app credentials. Record actual results in the live ledger rather than converting local fixtures into sponsor evidence.

Public source is published; its verified URL is in [the submission record](../submission.md). The narrated five-minute demo and contest submission remain separate delivery gates. Source excludes `.env`, databases, private archives, authentication and controller runtime state. No placeholder submission or post-deadline change is acceptable.

## Demonstrated local runtime lifecycle

The final operator and outbound Torob model worker run as user services on this demo workstation. Their private environment files and model authentication remain local and Git-ignored. This keeps them independent from terminal lifetime; it does not make the laptop an always-on hosted model service. A one-time local timer is scheduled for25October2026 at00:00UTC to request scale zero for only the three recorded disposable app IDs, preserving stored data. It is best effort and depends on this machine/session/network; it is not a provider-enforced billing cap or a claim that retained disks are free. The reviewed48-hour combined quote remains165024toman, within the200000toman scope; actual invoices were not inferred from that quote.

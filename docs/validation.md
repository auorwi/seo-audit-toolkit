# Validation scope

Validation is split by capability. Offline tests, controlled browser tests, live public requests and authenticated platform access are different evidence.

## Local release checks — 2026-10-15

Environment: macOS; Python 3.10.19, 3.12.13 and 3.14.3 were exercised. Browser/runtime validation used Python 3.14.3, Node 24.21.0 and Chrome 155.0.8059.41. Optional dependencies were installed into a fresh, isolated runtime directory from the public pinned package manifests; existing private runtimes and credentials were not copied.

- Final Python 3.10 regression run: 19 suites, 2,321 tests run, zero failures, one optional browser test skipped in the offline runner. The 18 specialist suites account for 2,264 tests; the optional browser test also passed in the separate real-browser run below. Python 3.12 and 3.14 passed the complete 2,320-test matrix before the last added runtime test, then passed the focused runtime checks with that test included.
- Compatibility regressions cover HTML attribute entity decoding, timestamp fractions/offsets, explicit read-only SQLite access, and runnable isolated Python virtual environments.
- New profile tests verify missing-profile errors, exact ASCII hosts and explicit punycode/default ports, Unicode-host rejection, unsafe URL rejection, independent profile changes, Python/JS parity and opt-in business behavior.
- Full ZIP relocation test: package extracted into a path containing spaces, installed into a temporary managed root, original extraction deleted, installed CLI and specialist help run successfully. The installed audit pipeline generated a report from controlled injected HTTP evidence; uninstall preserved the profile and report data. Real networking is a separate check.
- Browser launch/render probe passed using a separate browser profile.
- Controlled browser/extruct smoke: 51 tests passed with zero skips across generic collectors, TDK, semantics/axe, structured data, international, links and actual extruct extraction.
- Real local Lighthouse CI smoke: 2 tests passed, including a successful measurement and preservation of three failed HTTP attempts. These are controlled local pages, not production performance baselines.
- All seven generic browser collectors reached observable readiness with business identity explicitly unverified. A stronger wrong-identity case timed out, and an out-of-scope document redirect was blocked before its target fetch.

The unified HTTP public-site trial in the authoring environment was blocked because its DNS proxy resolved `example.org` to the reserved benchmark address range. The tool preserved this as an environment failure and did not weaken public-address checks or label it a website pass. An independent GitHub `public-http` run successfully acquired and parsed the example page in a public DNS environment; the workflow requires that real acquisition on subsequent runs too.

## CI and reproducibility

The [workflow](../.github/workflows/test.yml) runs:

- Offline regression suites on macOS and Ubuntu with Python 3.10 and 3.14.
- Package reference checks and the relocated ZIP lifecycle test on both OS families.
- Ubuntu browser installation, a real render probe, the controlled browser matrix and extruct tests.
- A bounded public HTTP smoke against one `example.org` page, without account access.

Use the GitHub Actions result for the exact release commit as the authoritative CI status. `python3 seo.py test` prints a suite summary with a separate skipped count; optional browser checks are skipped when the required runtime paths are absent. `scripts/browser_smoke.py` requires its selected controlled tests to execute without skips. An inherited live BingX acceptance test is excluded deliberately and has not been claimed as current validation.

## Not verified by these tests

- Native Windows, a separately provisioned WSL2 machine, and every Linux distribution/CPU architecture.
- A new user's Codex account/plan entitlement, model behavior in every conversation, or plugin-directory approval.
- Authenticated GSC/Bing/Yandex access, OAuth enrollment, platform quotas, or real Feishu publishing with someone else's account.
- Production website business semantics, rankings, indexing, rich-result display, or actual field CWV for arbitrary sites.

Chromium validates DNS but cannot pin the browser's socket address in this implementation; it is not a general-purpose network isolation sandbox. Test reports and fixture snapshots are not real search-engine verdicts.

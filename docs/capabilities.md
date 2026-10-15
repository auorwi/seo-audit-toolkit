# Capability and evidence matrix

The 18 original specialist engines remain separate. The unified `audit` command performs a quick initial-HTML review; the Codex `seo-audit` skill coordinates deeper checks using these modules. A module installed successfully may still require evidence, browser actions or an authorized platform account.

| Module | Inputs and collection | Output / boundaries |
|---|---|---|
| update-url | Public robots/sitemaps/link discovery; URL lists; browser/platform exports | Inventory and changes; discovery is not indexing or complete-site proof |
| sitemap | Inventory or saved XML/HTTP evidence; optional independent expected list | Sitemap structure, omissions and targets; independent source needed for completeness |
| crawlability | HTTP/robots/headers and optional DOM/engine evidence | Agent-specific directives and access observations; does not submit indexing |
| canonical-routing | Saved declarations, redirects, response evidence and entity review | Relationship graph and routing findings; cross-domain canonical is not automatically wrong |
| rendering | Initial HTML and stable DOM captures across entry paths | Content differences and gaps; navigation/interaction evidence must actually be collected |
| semantics | Browser capture with explicit scope; optional axe and local Nu executable | HTML/semantic observations; accessibility/HTML validity are not indexing verdicts |
| tdk | Browser and initial HTML captures, supplied context/review | Title/description grouping and draft directions; business intent still needs review |
| structured-data | JSON-LD captures; optional real extruct Microdata/RDFa extraction | Local structure/entity checks; rich-result eligibility/display needs engine evidence |
| internal-links | Browser DOM and actual target HTTP evidence | Observed links/discovery graph; unvisited targets and orphan candidates stay uncertain |
| international | HTTP/DOM/sitemap declarations, language/entity review | Hreflang and language relations; path names do not prove translation correctness |
| cwv | CrUX/PSI field evidence or own API key; repeated local LHCI measurements | Field and lab results stay separate; no available field data is not a pass |
| content-integrity | Browser/page facts and explicitly configured reference data | Internal consistency observations; market reference implementation is BingX-only opt-in |
| media | Browser image/video observations and resource evidence | Loading/selection/declaration checks; not video indexing certification |
| gsc | User-authorized browser/API response/export evidence | Historical indexing/performance observations; not a bundled OAuth/API client |
| bing | User-authorized UI/export/API response evidence | Historical, live test and recommendations separated; API parsing is not automatic collection |
| yandex | User-authorized UI/export/API response evidence | Exact host and timestamp-aware observations; online OAuth/quota integration not turnkey |
| recheck | Original IDs, old/new evidence, deployment context | Pass/partial/fail/inconclusive per issue; does not auto-close unrelated issues |
| report | Explicit manifest of specialist report files and SHA256 hashes | Local report/ledger; Feishu publishing optional via user's authenticated lark-cli |

## Invoking a specialist

```bash
python3 seo.py run sitemap --profile /absolute/path/profile.json -- --help
python3 seo.py run cwv --profile /absolute/path/profile.json --script collect_lab.py -- --help
```

Arguments after `--` go unchanged to the packaged script. Some scripts return `2` for partial coverage or review; consult their `SKILL.md` and references. Direct invocation of specialist scripts needs `SEO_SITE_PROFILE` in the environment. The root dispatcher sets it for you.

For browser capture:

```bash
python3 seo.py capture internal-links --profile /absolute/path/profile.json \
  --url https://example.org/ --output ./links-capture-001
```

Then read that module's `SKILL.md` and invoke its audit with the generated manifest and separate state. A capture is evidence collection, not the audit verdict. Semantics additionally needs the scope plan from `plan_scope.py`; pass `--scope /absolute/path/scope.json` after the root capture command's `--`. Explicit click/entry paths and body-language judgments remain evidence-driven agent work.

## Historical fixtures and business profiles

Regression tests retain synthetic and historical BingX examples. They are not live reports about BingX and never initialize another site's inventory. `profiles/bingx.json` is explicit opt-in; the default `init` command creates a generic profile. Generic sites do not call the BingX market API. Unsupported custom business reference systems remain unavailable until an adapter is implemented.

## What this release does not promise

- A single quick command completing every specialist and all platform UI reports.
- Search ranking gains, actual indexing, rich-result display or financial data correctness.
- Login/anti-bot bypass, server configuration changes or automatic production fixes.
- Native Windows compatibility or an individually certified WSL2 installation.
- Automated API access simply because the platform parsing skill is installed.

The initial specialist references are mostly Chinese; the setup/audit entrypoints and root guides support English and Chinese use. Codex can follow the specialist instructions in either conversation language.

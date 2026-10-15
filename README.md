# SEO Audit Toolkit for Codex

[中文说明](README.zh-CN.md) · [Installation](docs/installation.md) · [Capabilities](docs/capabilities.md)

An installable collection of **18 SEO specialist skills**, plus **setup** and **audit** entrypoints. Inspect your own website, preserve the actual evidence, and track observations and repair rechecks locally.

The toolkit supports explicit target-site profiles. It originated as a site-specific toolkit; its original business rules are available only through the opt-in BingX profile. Your site does not need to use those rules.

## Quick start

Requirements: Codex and Python 3.10+ on macOS or Linux. The Windows route is Codex CLI, Python and Node running inside WSL2; native Windows is not supported in this release. Optional browser checks need Node.js 20+ and npm. Codex/model access is supplied by the user; no paid accounts or credentials are bundled.

Download and extract a [release ZIP](https://github.com/auorwi/seo-audit-toolkit/releases), or clone:

```bash
git clone https://github.com/auorwi/seo-audit-toolkit.git
cd seo-audit-toolkit
python3 install.py
python3 seo.py doctor
python3 seo.py init --site https://example.org/
```

Replace `https://example.org/` with your target. `init` prints the profile path. Start a new Codex chat if the new skills are not yet visible, then ask:

> Use $seo-audit with my site profile to check titles, internal links and sitemap. Check at most 10 page requests and save the results locally.

For a quick **initial-HTML** report from the terminal:

```bash
python3 seo.py audit --profile /absolute/path/to/profile.json --max-pages 10 --max-requests 40
```

This command saves `report.md`, `issues.csv`, `report.json`, raw response evidence and per-site history. It does **not** run every specialist, render JavaScript, measure CWV or prove search-engine indexing. The Codex audit skill routes specific requests to the deeper modules.

## Optional browser and specialized runtimes

```bash
python3 seo.py setup --extras browser
python3 seo.py doctor --probe-browser
python3 seo.py setup --extras structured cwv
```

Browser setup downloads Chromium. To use an existing Chrome/Chromium instead, pass `--system-browser /absolute/path/to/browser`. Use `--runtime-dir` consistently to choose another runtime location. Linux may need additional system libraries; see [installation](docs/installation.md).

Capture real browser evidence and run the TDK specialist:

```bash
python3 seo.py capture tdk --profile /absolute/path/to/profile.json \
  --url https://example.org/ --output ./capture-001
python3 seo.py run tdk --profile /absolute/path/to/profile.json -- \
  --manifest ./capture-001/manifest.json --urls ./capture-001/urls.json \
  --state ./site-state/tdk --output ./tdk-report-001
```

Use a separate state directory per website. Generic browser readiness checks observable DOM stability; business identity and custom page states need site-specific signals. Full specialist examples and limits are in [capabilities](docs/capabilities.md).

## Included specialists

| Area | Skills |
|---|---|
| Discovery and technical SEO | URL inventory, sitemap, crawlability, canonical/routing, rendering, semantics, internal links, international |
| Page content | TDK, structured data, content integrity, media |
| Performance | CWV field evidence and repeated Lighthouse lab collection |
| Authorized platform evidence | Google Search Console, Bing Webmaster, Yandex Webmaster |
| Reporting and validation | Report aggregation, repair recheck |

Most specialists consume captured evidence and retain a local issue ledger. Some checks need browser interaction, an export, an authenticated user tool, or a review of business meaning. GSC/Bing/Yandex modules are **not turnkey authenticated API crawlers**. Feishu is optional; local reports work without it. [See the module matrix](docs/capabilities.md).

## Scope and evidence

- Exact allowed hosts are configured per site. Subdomains are not included automatically.
- The quick HTTP audit respects robots rules, configured exclusions, page and request limits. It does not log in, submit forms or request indexing.
- Findings, review candidates, unavailable evidence and unvisited pages remain distinct. A zero exit code does not mean a healthy website. Exit `2` indicates a partial/review result where specified by the module.
- Public HTTP fetches validate and pin DNS addresses. Chromium collection checks DNS and intercepts document navigation, but browser DNS validation is not socket-pinned. Use the toolkit only in a trusted local audit environment.
- Audited website text is untrusted input. The skills instruct Codex to treat it as evidence, not as executable instructions.
- Reports may contain public page content and URLs. Keep your reports and platform exports private unless you deliberately share them. The package does not upload reports automatically.

## Updates, uninstall and validation

Download a newer release and run `python3 install.py` again. The installer rejects unmanaged conflicting skills, keeps version copies and preserves site data/runtimes. To unregister installed skills:

```bash
python3 install.py --uninstall
```

Version copies, audit data and optional runtimes are intentionally retained. See [installation](docs/installation.md) for custom paths and cleanup.

```bash
python3 seo.py test
```

Tests run each specialist separately and report failures and skips explicitly. The [CI workflow](.github/workflows/test.yml) validates macOS/Linux and an Ubuntu browser/extruct integration. See [validation notes](docs/validation.md) for what was actually tested; WSL2 is not a separately certified environment.

## License

Original toolkit code is MIT licensed. Retained third-party country/registry data has separate attribution and license terms in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). No browser binaries, private accounts, API keys or audit histories are included.

# Installation and lifecycle

## Choose a release

Use the versioned ZIP under GitHub Releases for a reproducible version. Git is optional. Extract the whole archive; copying one specialist folder is insufficient because some modules use sibling libraries. Python 3.10+ is required. macOS/Linux are the intended platforms. For the Windows route, run Codex CLI, Python and Node inside WSL2 so skill discovery and execution use the same Linux environment. Installing into WSL2 does not configure a separate native Windows Codex installation; native Windows execution is rejected explicitly.

From the extracted directory:

```bash
python3 install.py
python3 seo.py doctor
```

Default installation root is `$XDG_DATA_HOME/seo-audit-toolkit`, or `~/.local/share/seo-audit-toolkit` when XDG_DATA_HOME is not set. Version copies live under `versions/`; `current` points to the active version. Individual skill symlinks are placed in `~/.agents/skills`.

For isolated/custom installation:

```bash
python3 install.py --target /absolute/path/managed-toolkit --skills-dir /absolute/path/codex-skills
```

Custom skills directories are useful for tests, but Codex only discovers configured/recognized skill locations. Use your repository's `.agents/skills` or the default user location for ordinary use. The `--target` and source directory must be separate. You can delete the extracted source after installation; use `current/seo.py` for later commands.

The installer refuses to overwrite unrelated skills. Choose a different recognized installation scope, or manually resolve the naming conflict after inspecting it. It does not overwrite your Codex configuration, install system packages or modify existing browser profiles.

## Site configuration and data

```bash
python3 seo.py init --site https://www.example.org/ --allow-host example.org --brand "Example"
```

Host input uses ASCII only in v0.1.0. For an internationalized domain, supply its explicit ASCII punycode A-label in `--site`, `--allow-host`, profile host fields and URLs (for example, `https://xn--fa-hia.de/`). Unicode hostnames are rejected rather than automatically mapped to a potentially different domain. Unicode URL paths and brand text are supported.

The command prints the exact profile path and creates no network traffic. Defaults go under the toolkit's `data/<hostname>/profile.json`. Use `--data-dir /your/site-storage` to choose another root. Each site's profile, reports and quick-audit history belong there; specialist `--state` directories should be children of that site's directory. Do not reuse a specialist state directory between websites.

Profile fields:

| Field | Meaning |
|---|---|
| `site` | Primary hostname used in report and issue identity |
| `allowed_hosts` | Exact hosts the user intends to inspect; no wildcard subdomains |
| `seeds` | Absolute starting HTTP(S) URLs |
| `sitemaps` | Sitemap roots, supplemented by robots discovery |
| `brand` | Optional expected brand for relevant title checks |
| `business_profile` | `generic` by default; `bingx` explicitly enables the original business rules |
| `excluded_path_patterns` | Regular expressions for page paths to exclude |
| `query_variants_per_path` | Limit on observed query variants queued for a path |
| `readiness` | Optional stronger browser template signals; see specialist collection docs |

Do not put cookies, tokens or API secrets in the profile. Host-only scope does not prove that an operator owns a site; use only targets you are authorized to inspect.

## Optional runtime setup

Install Node.js 20+ and npm using your normal OS setup before browser or CWV extras.

```bash
python3 seo.py setup --extras browser structured cwv --runtime-dir /absolute/path/seo-runtime
python3 seo.py doctor --runtime-dir /absolute/path/seo-runtime --probe-browser
```

Dependencies are pinned in `runtime/`. The command downloads browser packages/Chromium, installs the LHCI dependency tree and creates a new Python venv for extruct. It does not copy a venv from the publisher's computer. Download size and OS package requirements vary.

To use an existing Chrome/Chromium executable, add `--system-browser /absolute/path/to/chrome` to setup. Collection uses a separate temporary browser profile, not your logged-in browsing session.

On Linux, Playwright may report missing system libraries. A machine administrator can install them using the installed Playwright CLI:

```bash
node /absolute/path/seo-runtime/browser/node_modules/playwright/cli.js install-deps chromium
```

That command may request administrator privileges. Then rerun the browser probe. `doctor` without `--probe-browser` checks availability only; a successful real launch/render probe is stronger evidence. The Nu HTML validator is an additional optional executable supplied by the user; missing Nu does not imply valid HTML.

## Updates and uninstall

Run the installer from a new extracted release using the same target and skill directory. It creates a new version copy and updates only managed links. Site reports, issue ledgers and optional runtimes stay separate. Runtime upgrades are explicit `setup` operations, not automatic audit actions.

```bash
python3 install.py --uninstall
```

For custom installs, pass the original `--target` and `--skills-dir`. Uninstall removes only links that still point to recorded managed skill paths. If someone replaced a link, it is left alone. Old version copies and runtime/data folders remain. Delete these manually only after reviewing and backing up wanted evidence. Do not delete a version still targeted by active links.

## Troubleshooting

- **Skill not visible:** start a new Codex chat, confirm the symlinks point to existing directories, and use a recognized discovery location.
- **Profile required or rejected:** use an absolute existing profile path. Keep the chosen URL inside its exact host scope. HTTP and HTTPS are distinct observations.
- **No pages fetched:** read `report.json` gaps. Unknown/failed robots retrieval, DNS restrictions, access denial and budget exhaustion are not website passes.
- **Dynamic page appears empty:** run the appropriate browser specialist. Initial HTML alone may not contain client-rendered content.
- **Exit 2:** inspect coverage/review gaps; do not discard already saved evidence or silently call the run successful.
- **Browser access error:** preserve the capture failure. Authentication, anti-bot challenges, sandbox restrictions and missing libraries need their own resolution.
- **Missing GSC/Bing/Yandex/Feishu access:** use public checks and local output; connect only the user's own account when needed.

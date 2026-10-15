---
name: seo-setup
description: Set up the SEO Audit Toolkit in Codex when installing it, checking missing dependencies, adding a target website, or enabling browser, structured-data or performance checks.
---

# Set up a website audit

Resolve this skill directory through symlinks. The toolkit root is two directories above it and contains `seo.py`. Use the complete package; the specialist folders share libraries.

1. Run `python3 "<ROOT>/seo.py" doctor`. Base HTTP checks require Python 3.10+ on macOS/Linux; browsers and platform accounts are optional. Windows uses WSL2; consult the platform validation table in [the README](../../README.md).
2. Use the user's target URL. If there is no configured site yet, run:

   ```bash
   python3 "<ROOT>/seo.py" init --site "https://example.org/"
   ```

   Read the returned profile path. Replace the example with the actual target. Existing profiles are never overwritten. Add subdomains explicitly with `--allow-host`; a parent domain does not authorize all subdomains. Each host has a separate site data directory. Never default to the bundled BingX profile or historical sample URLs.
3. For a quick public HTTP check, no extra installation is needed. For browser evidence, use `setup --extras browser`; for Microdata/RDFa use `setup --extras structured`; for lab performance use `setup --extras cwv` and a browser. Runtime downloads can be large. Use `--runtime-dir` to choose storage, and `--system-browser` when the user prefers an existing browser executable. The runtime commands install only the requested extras.
4. After browser setup, run `doctor --probe-browser` (same runtime directory). Only a successful actual launch/render probe verifies it works. On Linux, missing OS libraries may require an administrator; show the actual error and the documented dependency command. Do not mark skipped probes successful.
5. Hand off the profile and capability results to `$seo-audit`. Keep all website evidence outside installed skill directories.

The [installation guide](../../docs/installation.md) covers ZIP installation, updates, conflicts and uninstall. Optional webmaster/Feishu setup uses each user's own access; never copy credentials or browser profiles from another machine. Without those integrations, continue with public pages and local reports and record the unavailable capabilities.

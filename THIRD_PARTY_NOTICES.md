# Third-party notices

The MIT license in the root applies to original toolkit code, not to third-party data or downloaded dependencies.

- `skills/seo-international/references/data/iso3166-1.json` is retained from pycountry's country database, based on iso-codes. Its provenance is in `country-source.json`; the retained license is `pycountry-LICENSE.txt` in the same directory. The file is redistributed without replacing those terms with MIT.
- `skills/seo-international/references/data/language-subtag-registry.txt` is a snapshot of the IANA Language Subtag Registry. Its source URL, capture date and digest are recorded in `registry-source.json`. It is reference data, not a guarantee about current registrations.
- Browser extras download Playwright/Chromium and axe-core; CWV extras download Lighthouse CI and its dependency tree; structured-data extras download extruct and its dependencies. Their licenses remain those of the respective packages. Lockfiles record exact versions and, where provided by npm, package license metadata.
- Browser binaries and third-party runtime installations are downloaded on the user's machine and are not included in the source release ZIP.

Country source: https://github.com/pycountry/pycountry

Language registry source: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry

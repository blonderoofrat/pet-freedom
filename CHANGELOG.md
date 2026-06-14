# Changelog

All notable, user-facing changes to the Pet Freedom skill are recorded here, newest at the top.
Versions follow semantic versioning, MAJOR.MINOR.PATCH:

- **MAJOR** is a breaking change (config.json, the data schema, or how you run the skill changes in a way
  that needs you to do something).
- **MINOR** adds features in a backward-compatible way.
- **PATCH** is a fix or a small improvement.

When Claude checks for updates, it reads this file to tell you, in plain language, what changed since your
installed version, before applying anything. Keep the newest version here matching the `VERSION` file.

## 1.0.0 (2026-06-13)

First public release.

- Research, verify, and publish the legal status of a species (keeping, breeding, selling, transport)
  across many jurisdictions, as a structured, source-cited WordPress resource.
- Species-agnostic: everything species- and site-specific lives in `config.json`.
- Privacy-preserving: your credentials and private notes stay on your machine; published pages render only
  public-safe fields.
- Offline tooling (Python standard library only, no `pip install`): seed jurisdictions, render and publish
  (`build.py`), audit for certainty (`audit.py`), generate Deep Research prompts, export a scrubbed demo
  seed (`export_seed.py`), and build a WordPress Playground demo (`playground.py`).
- Optional written agency-inquiry workflow to close verification gaps, plus a branch-aware advocacy toolkit.
- Optional companion WordPress plugin for a friendly admin page and a uniform SEO post-meta route; a
  no-plugin SEO fallback (`mu-plugin/register-seo-meta.php`) is included.
- Two-register voice guide (factual for legal and advocacy text, the owner's own voice for posts), and the
  preservation rules for native spelling and verbatim official quotes.
- Self-test harness (`skill/selftest.py`) that verifies the whole offline pipeline against the bundled demo
  corpus, so an update can be confirmed not to have broken anything.
- Self-update tool (`skill/update.py`): checks GitHub for a newer version, shows the changelog, and applies a
  non-breaking update with a self-test gate and automatic rollback on failure (a breaking update pauses for
  confirmation). Your `config.json` and `data/` are never touched.

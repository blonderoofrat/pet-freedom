# Changelog

All notable, user-facing changes to the Pet Freedom skill are recorded here, newest at the top.
Versions follow semantic versioning, MAJOR.MINOR.PATCH:

- **MAJOR** is a breaking change (config.json, the data schema, or how you run the skill changes in a way
  that needs you to do something).
- **MINOR** adds features in a backward-compatible way.
- **PATCH** is a fix or a small improvement.

When Claude checks for updates, it reads this file to tell you, in plain language, what changed since your
installed version, before applying anything. Keep the newest version here matching the `VERSION` file.

## 1.2.2 (2026-06-15)

- RUNBOOK: the assume-a-pathway lens now warns that an unlisted or unaddressed species does NOT automatically
  mean unregulated or legal. Determine the jurisdiction's default rule first: an open regime (anything not
  prohibited is allowed) makes an unlisted species unregulated or legal, but a closed positive-list regime
  (only approved species allowed) makes it prohibited, and often permit-ineligible. Verify both directions,
  since a place can look banned yet still permit the common pet species, or look permissive yet quietly
  exclude the niche species (a species trap).
- audit.py now also flags, as a soft voice warning, any public-rendered prose (the summary, an activity
  "why", a restriction summary, or an agency confirmation) that contains an em-dash, so it can be smoothed to
  commas or periods before publishing. Em-dashes inside a quoted official source are fine and should be left.
- SKILL.md: at session start the skill now proactively offers to pre-authorize read-only web access
  (`WebFetch`/`WebSearch`) instead of letting you be prompted to approve each research URL, since those fetches
  follow directly from the research you asked for. Per-URL prompting during verification is wasteful friction;
  one allow-list entry removes it and loosens nothing destructive.

## 1.2.1 (2026-06-14)

- Documentation, from a real outage: `docs/EMAIL-DELIVERABILITY.md` now covers **MX records** (so agency
  replies reach you, not just SPF/DKIM/DMARC for sending) plus a "verify both directions before you rely"
  checklist. `docs/RUNBOOK.md` section 9 adds the inquiry retry/reply methodology: try all listed addresses,
  email first with a web-form fallback after ~a week on no-reply/bounce, bounce triage, and processing
  replies (an agency answer outranks Deep Research).

## 1.2.0 (2026-06-14)

- The agency-inquiry mailer (`skill/mail.py`) now keeps a record of everything you send. Each send is saved
  locally to `data/sent_archive/<date>.eml` plus an index line in `data/sent_log.jsonl` (independent of your
  mail server), and, unless your provider auto-saves sent mail, a copy is appended to your mailbox's Sent
  folder so it shows in webmail. New `python skill/mail.py sent` lists the record.
- New `python skill/mail.py verify`: checks SMTP + IMAP login and detects your Sent folder, then reports how
  the Sent copy will behave on your provider. It sends nothing. Run it before relying on the mailer.
- New optional `.env` settings so the Sent copy works across providers: `SITE_MAIL_COPY_TO_SENT`
  (auto / always / never; use `never` on Gmail/Outlook, which auto-save) and `SITE_MAIL_SENT_FOLDER` (exact
  Sent-folder name if auto-detection fails). The local archive is always kept regardless.

## 1.1.0 (2026-06-13)

- On a successful publish, the skill now records its version to the companion plugin (a new admin-only
  `/skill-version` route), so the plugin's Get Started page can show which skill version last built the site.
  This is a drift signal: if it is newer than the plugin expects, update the plugin. It is a no-op without the
  companion plugin or in no-plugin mode, and never fails the build. (Companion plugin 1.4.0 adds the display.)

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

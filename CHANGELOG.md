# Changelog

All notable, user-facing changes to the Pet Freedom skill are recorded here, newest at the top.
Versions follow semantic versioning, MAJOR.MINOR.PATCH:

- **MAJOR** is a breaking change (config.json, the data schema, or how you run the skill changes in a way
  that needs you to do something).
- **MINOR** adds features in a backward-compatible way.
- **PATCH** is a fix or a small improvement.

When Claude checks for updates, it reads this file to tell you, in plain language, what changed since your
installed version, before applying anything. Keep the newest version here matching the `VERSION` file.

## 1.3.5 (2026-08-03)

- **Demo dataset: Austria updated to a new official agency confirmation.** Austria's health ministry
  (BMASGPK) answered in writing, under an official signature, that the roof rat is **not a domesticated
  animal**. That one classification decides the rest: rodents count as pets in Austrian law only if
  domesticated, so *Rattus rattus* falls into the residual "wild animal" category instead. Keeping stays
  lawful, but only after filing a notification with the district authority within two weeks; breeding needs
  no second filing, because a 2026 provision folds the breeding report into that same notification; and a
  real permit is triggered only above 300 juveniles given away per year, which is far beyond a hobby colony.
  The entry previously reasoned its way to the same route and said a written ruling would confirm it. It has,
  so the hedging is gone and the citations are now exact. Re-exported from the live source; the name backstop
  re-verified 0 private-data leaks. Data-freshness update, no schema or methodology change.
- **Agency contacts now name the office, not the individual officer.** Seven demo jurisdictions (Alberta,
  Switzerland, Finland, Alabama, Arkansas, Hawaii, Rhode Island) attributed a written agency reply to the
  named civil servant who sent it, and three of them carried that person's direct work email in the contact
  block, two with a direct phone. Those entries now cite the agency, the role and the reference, and point at
  the office channel. This matches the guidance the skill itself gives, and it is the right default for a
  dataset anyone can fork: an official who answers a research question should not inherit a public inbox from
  it. No legal substance changed anywhere; every ruling, citation and date is exactly as before.

## 1.3.4 (2026-07-10)

- **Hub browse: a country whose regions disagree now shows a "varies by region" hint.** A country badged
  "Legal" that has some sub-jurisdictions where it is prohibited or restricted (for example the United States,
  legal nationally but banned in some states) now carries a small dashed "varies by region" chip beside its
  badge, so the row is honest at a glance instead of reading as a flat national "Legal" above a list of bans.
  This does not change any recorded status; it is derived purely from the children. Mirrors the same improvement
  on the main roof-rat site (the skill's renderer is kept in sync with it).

## 1.3.3 (2026-07-08)

- **Demo dataset: Hong Kong updated to a new official agency confirmation.** Hong Kong's AFCD (Agriculture,
  Fisheries and Conservation Department) confirmed in writing that it does not regulate the keeping of rats
  (keeping a pet roof rat is lawful, no keeping permit), but it will not issue an import permit for *Rattus
  rattus* as a pet because the species is a designated rodent-control pest, so **pet import is now prohibited**
  (a keep-legal, import-barred, source-locally jurisdiction). A licensed animal-trade premises' mandatory
  mammalian-pest-control programme also conflicts with a commercial trade in the species. Re-exported from the
  live source; the name backstop re-verified 0 private-data leaks. Data-freshness update, no schema or
  methodology change.

## 1.3.2 (2026-07-02)

- **Demo dataset refreshed to the latest verified jurisdiction data.** Re-exported the roof-rat reference dataset
  from the live source, picking up recent official agency confirmations and status updates: the **Philippines is
  now prohibited** (confirmed by DENR-BMB), and **Czechia** and **Taiwan** carry new official **agency
  confirmations**; several US/Canada entries also got their latest verified status calls and stale-text cleanups.
  No methodology or schema change, this is a data-freshness update. The export scrubber's name backstop re-verified
  0 private-data leaks.

## 1.3.1 (2026-06-24)

- **The "not on the list" trap (non-native species) — new methodology guardrail.** A non-native species being absent
  from the invasive/alien-species named lists does NOT by itself mean keeping it is legal. Many alien-species laws add
  a **general clause covering any alien species**: most ban only **release/introduction into the wild** (keeping a
  caged pet stays legal, so unlisted = legal — the common case), but a minority extend the ban to **keeping itself**,
  making an unlisted species prohibited to keep (e.g. Finland's Invasive Species Act §3; Norway's Exotic Animal
  Regulation positive list). The skill now tells you to read the operative *verb* (keeping vs release), get the
  exotic-pet list polarity right (positive list → unlisted prohibited; negative list → unlisted allowed), probe with
  the domesticated relative, and not over-correct (most general clauses are release-only). New `SKILL.md` §3.1, a
  pointer in the per-jurisdiction loop (step 5), an expanded probe in the research prompt template, and a country-layer
  note in `docs/SOURCES.md`. No code or schema change; nothing to do but pull.

## 1.3.0 (2026-06-20)

- **City & county (municipal) layer.** `build.py` now renders a "Local city & county rules" section on a parent
  jurisdiction page (its city/county children with status badges) and nests cities under states in the hub, so a
  municipality page is never orphaned. A city is just a jurisdiction JSON with `level:"municipality"` + `parent` =
  its state id; URLs nest under the state.
- **Municipal methodology (RUNBOOK new §12):** the 4-state coverage model (presumed / suspected / researched-
  stricter = full page / researched-not-stricter = reassurance stub), the city-screening rule (only large metros in
  permissive states with a home-rule signal; skip states that already restrict), and screen-free-first (read the
  code with a headless fetch or a full-text mirror; escalate to Deep Research only when a code host is unreadable).
- **Demo refreshed** to include worked city examples so the playground shows the new city layer.

## 1.2.5 (2026-06-18)

- **RUNBOOK §9 safety guardrail, remediation half: if a flawed inquiry template already went out, audit your
  ENTIRE sent archive in EVERY language.** The 1.2.4 guardrail covers prevention; this adds what to do once a
  bad send is discovered. A defect in a shared template (a wrong residency line, an over-claim of possession)
  rides every *translated* copy, so an English-only spot-check misses the rest. When you find one, re-scan all
  sent inquiries across all languages before concluding you have caught them, then correct each affected thread
  in that thread's language, reviewing every correction before it sends. Learned the hard way: a first
  correction pass caught the English misrepresentations but missed the French and Vietnamese copies of the same
  template bug; a full multi-language re-sweep found them.

## 1.2.4 (2026-06-16)

- **Safety guardrail in RUNBOOK §9 (Inquiries): never misrepresent yourself to a government agency.** When you
  email agencies to confirm a species' legal status, do not claim to be a resident of, or to keep/breed/import
  the animal in, a jurisdiction where you do not live (and especially not one where it is restricted). A false
  residency claim, or implying you possess a regulated animal in their territory, can expose YOU to legal
  jeopardy. Write as what you are: someone compiling a guide for the benefit of that jurisdiction's residents,
  explicitly "not a resident there, not seeking to keep or import there." This matters most for shared templates
  sent to many jurisdictions. Also added: verify you are emailing the right office/role (use only verified
  contacts, not an address copied from another thread), and honor any request to stop or switch inboxes. Learned
  the hard way; published so adopters never repeat it.

## 1.2.3 (2026-06-15)

- New `docs/SOURCES.md`: a species-agnostic directory of WHERE the authoritative primary law lives (primary-law
  portals by region, the US-federal and EU/CITES supranational layers, and a strong secondary corroborator),
  plus the "layer checklist" (the predictable order to check a jurisdiction's rules) and the field-learned
  reliability caveats. RUNBOOK §6 and SKILL.md now point to it as the starting point for verification, so research
  begins from known-good sources. Listed by role (never personal contacts or private archives); a living file to
  keep current as sources prove out or move.

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

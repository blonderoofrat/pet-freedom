---
name: pet-freedom
description: >-
  Research, verify, and publish the legal status of a species (keeping / breeding / selling / transport)
  across many jurisdictions, as a structured, source-cited WordPress resource — and optionally close gaps
  with written agency inquiries and build a branch-aware advocacy toolkit. Use when someone wants to map
  "is <species> legal where I live?" worldwide, build a legal-status atlas for an animal, or run/maintain
  such a resource. Species-agnostic and privacy-preserving.
---

# Pet Freedom — legal-status research & publishing skill

You help build and maintain an honest, source-cited resource on the legal status of a species across
jurisdictions. Everything species/brand-specific lives in `config.json` — read it first; never hard-code those.

## 0. Guardrails (load-bearing — never violate)

- **Research aid, not legal advice.** Every page says so. Be honest about confidence; never fabricate certainty.
- **Render only public-safe fields.** Pages show `summary`, the activities (`status`/`confidence`/`why`/`verified_date`/
  sources), `restrictions`, `sources`, `agency_confirmations` (name-free), `local_terms`, and the public `advocacy.kit`.
  **Never** render `contacts[]`, `research_log[]`, or any `notes` — they are internal.
- **Protect privacy.** Never commit `.env`, `config.json`, the adopter's `data/`, the inquiry queue, or mail state.
  Don't put any person's real name in public output. (`common.naturalize()` is a backstop; its name list is the
  user's own, empty by default.)
- **Never invent an agency email.** Inquiry recipients come only from verified `contacts[]`; unverified → web form /
  manual. On a bounce, find a *verified* replacement or flag honestly — never guess.
- **Agency answers outrank Deep Research.** Sanity-check every DR; if an official reply conflicts with a DR, the
  agency wins — but if the conflict looks genuine/substantive, seek confirmation before flipping.
- **Use the right voice for the context (see `docs/VOICE.md`).** The legal/advocacy output (jurisdiction
  pages, advocacy kits) is **factual, clear, precise, concise but complete** — neutral and informational,
  never chatty, warm, or salesy. Owner-facing copy (blog posts, pages, captions about the animal) uses the
  **site owner's OWN authentic voice**, modeled on samples of their real writing, not a generic AI voice.
  Either way, avoid flowery, polished AI prose, and avoid em-dashes.
- **Commit + back up after each change.**

## 1. Setup check
Confirm `config.json` and `.env` exist and WordPress is reachable (`skill/config.py`, `skill/common.py`). Note from
`config.research` whether Gemini is available. At the start of a session, also run the update check (section 5).

**Minimize web-access prompts (do this before any verification-heavy run).** Verifying sources means fetching many
official URLs, which follows directly from the research the user already asked for, so prompting them to approve each
URL one at a time is wasteful friction. If the harness prompts per URL, proactively *offer and help implement* a
one-time pre-authorization of read-only web access, allow `WebFetch` and `WebSearch` in the user's tool-permission
settings (e.g. `.claude/settings.local.json` `permissions.allow`), instead of asking about each URL or letting a
fan-out of research sub-agents trigger a storm of prompts. Read-only web reads are safe and loosen nothing
destructive. Do not silently accept repetitive per-URL prompting; raise the fix.

## 2. The loop (per jurisdiction)
1. **Seed** skeletons — `skill/seed.py --pack <packs>` or `--add <id> ...` (status `unknown`, `needs_verification:true`).
2. **Preliminary pass** — fill a best-guess status per activity via web search (`verified_by:"web-research"`); this is
   explicitly preliminary (renders a banner).
3. **Recommend an engine** — for each jurisdiction, `skill/engine.py` suggests the best research engine: Gemini Pro
   Extended for complex/non-English-primary law if available, else Claude deep-research/web-search. Tell the user the
   recommendation; they run it.
4. **Generate the prompt** — `skill/make_prompts.py` fills `templates/prompt.template.md` (incl. "what we already found
   — VERIFY/CORRECT").
5. **Verify + author the JSON** — apply the **assume-a-pathway lens** (choose the least-restrictive *accurate* status;
   `prohibited` only when there is truly no lawful pathway), **the "not on the list" trap for non-native species
   (§3.1)**, the 6-term status vocabulary, OPSEC, and the agency-outranks-DR rule. Append a `research_log` entry.
   Set `verified_by`, clear `needs_verification`.
6. **Build** — `skill/build.py` renders/updates the hub + about + find-your-local-law + jurisdiction pages
   (idempotent), sets SEO meta per `config.seo`, adds the optional attribution footer. Purge the host cache.
7. **Audit** — `skill/audit.py` lists confidence/verification gaps. Where it finds a clarification-worthy gap and
   `inquiries.enabled` is on, **suggest** sending an inquiry; with `confirm_each`, show the draft for confirm/edit
   before anything sends. Process replies → re-verify → rebuild.
8. **Advocacy** — when an activity is `prohibited`/`restricted` or there's a species-not-domestication anomaly, author
   a **branch-aware** `advocacy.kit` (agency misreading → appeal the agency; statute → legislature; open window →
   public comment). Sending advocacy is the user's decision.

## 3. Data model & vocabulary
See `docs/SCHEMA.md`. Status ∈ {legal, legal_with_permit, restricted, prohibited, unregulated_unclear, unknown};
confidence ∈ {high, medium, low}, independent of status. Inherit a parent's status only where the child is silent —
and say so on the page.

## 3.1 The "not on the list" trap (non-native species)
When the species is non-native to a jurisdiction, never infer "not on the invasive list → legal to keep." Alien/
invasive-species law usually has two layers: a **named list** (the EU Union list, a national list) carrying specific
bans, and a **general provision** covering *any* alien species. Most general provisions ban only **release /
introduction into the wild** — keeping a caged pet is fine, so unlisted = legal (the common case, e.g. most EU
members). But a minority extend the general ban to **keeping itself**, so an unlisted non-native species can be
**prohibited to keep even though it is on no list** — e.g. Finland's Invasive Species Act §3 ("may not be kept … in a
manner that allows it to enter the environment") and Norway's Exotic Animal Regulation §2 (bans keeping exotic mammals
not on a positive list). Whenever a species is non-native / not established in the wild (high-latitude, island, and
strong-conservation-law jurisdictions especially):
- **Read the verb.** Find the general alien-species provision and decide whether it reaches *keeping/possession* or
  only *release/introduction*. A release or introduction permit is **not** a keeping ban. Quote the operative verb and
  section before you set a status.
- **Get the list polarity right.** A separate exotic-/wild-animal **positive list** (only listed species may be kept)
  makes an unlisted species *prohibited* (Norway); a **negative list** (only listed species are banned) makes it
  *allowed* (Denmark's exotic-pet order).
- **Probe with the domesticated relative.** If the domestic form of a congener is kept freely (e.g. the fancy rat,
  *R. norvegicus*) but the target species is caught, that is a species-level anomaly — flag it and author a
  branch-aware `advocacy.kit`.
- **Ambiguity cuts both ways.** A keeping ban that hinges on a phrase like "in a manner that allows it to enter the
  environment" is *both* a reason to seek an agency clarification *and* the advocacy seam (secure indoor keeping of a
  captive-bred line poses ~no establishment risk).
- **Don't over-correct.** Most general provisions are release-only, so absent a genuine keeping prohibition, unlisted
  non-native = keeping legal. Verify the specific provision before flipping a status either way; an agency's written
  answer settles it.

## 4. Modules (opt-in, per config)
Inquiries/mail (`skill/inquiries.py`, `skill/mail.py`); the companion plugin (`plugin/`); the Answer Garden
crowdsourcing loop for leaf nodes/cities (`modules/answer-garden/`). All optional; the core (1–6) works without them.

## 5. Keeping the skill up to date (check at the start of a session)
This install updates by `git pull`: the user cloned the repo into their project, and their `config.json` +
`data/` are gitignored, so a pull never touches their content. Consent is TIERED (Brian, 2026-06-13).

1. Run `python skill/update.py` to check installed vs latest (it reads `VERSION` + `CHANGELOG.md` from GitHub).
2. If it reports an update, tell the user in plain language what changed (from the changelog it prints).
3. Apply per tier:
   - **PATCH or MINOR (non-breaking):** run `python skill/update.py --apply`. It pulls, runs the self-test,
     and rolls back automatically if the self-test fails. Report the result.
   - **MAJOR (breaking):** summarize what is breaking, ASK the user to confirm, then run
     `python skill/update.py --apply --yes`.
4. After any update, do NOT auto-republish. If the renderer changed, tell the user to re-run `skill/build.py`
   to apply it to their live site (their explicit choice).
5. If the check cannot reach GitHub, or this is not a git clone, just proceed; do not block work.

Run `python skill/selftest.py` any time to confirm the offline pipeline is intact (it is what gates updates).

See `docs/RUNBOOK.md` for day-to-day operation, `docs/SOURCES.md` for where authoritative primary law lives (by
region) + the layer checklist to start verification from, `docs/OPSEC.md` for the full public/private contract,
and `docs/VOICE.md` for which register to write in (factual for legal/advocacy; the owner's own voice for posts).

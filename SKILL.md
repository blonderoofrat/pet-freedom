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
- **Commit + back up after each change.**

## 1. Setup check
Confirm `config.json` and `.env` exist and WordPress is reachable (`skill/config.py`, `skill/common.py`). Note from
`config.research` whether Gemini is available.

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
   `prohibited` only when there is truly no lawful pathway), the 6-term status vocabulary, OPSEC, and the
   agency-outranks-DR rule. Append a `research_log` entry. Set `verified_by`, clear `needs_verification`.
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

## 4. Modules (opt-in, per config)
Inquiries/mail (`skill/inquiries.py`, `skill/mail.py`); the companion plugin (`plugin/`); the Answer Garden
crowdsourcing loop for leaf nodes/cities (`modules/answer-garden/`). All optional; the core (1–6) works without them.

See `docs/RUNBOOK.md` for day-to-day operation and `docs/OPSEC.md` for the full public/private contract.

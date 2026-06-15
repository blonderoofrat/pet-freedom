# RUNBOOK — day-to-day operation

This is the loop you run, per jurisdiction, from a clean install. The agent (`SKILL.md`) drives most of it;
the **human-in-the-loop** steps — run the research, validate the result, decide on inquiries/advocacy, purge
the cache — are called out as you go.

> **A research aid, not legal advice.** You own the accuracy of what you publish. Be honest about
> confidence; never fabricate certainty.

The whole loop:

```
seed → preliminary pass → recommend engine → generate prompt
     → (human) run Deep Research → paste back → verify + AUTHOR the JSON
     → build → PURGE CACHE → audit → (optional) inquiries → (optional) advocacy → sweep
```

**Commit + back up after every change.** (See the habit at the bottom.)

---

## 1. Seed the skeletons

Turn a starter pack (pure public geography) into one `data/jurisdictions/<id>.json` skeleton per place:

```bash
python skill/seed.py --pack us-states world-major
```

Or add one place by hand:

```bash
python skill/seed.py --add us-tx --level state --parent us --name "Texas" --country US --language en
```

Each skeleton starts at `status:unknown`, `needs_verification:true`, `verified_by:"web-research"`, with
`local_terms` filled from your configured species. The seeder **never clobbers verified data**: a file that
has graduated (any activity verified by a real source, `needs_verification:false`) is skipped.

## 2. Preliminary pass

For each skeleton, the agent fills a best-guess status per activity from web search and writes a one-line
`summary`. This stays explicitly preliminary (`verified_by:"web-research"`, `needs_verification:true`) — it
renders a clear "Preliminary" banner — and exists so the Deep Research has a working answer to confirm or
overturn.

## 3. Recommend a research engine (per jurisdiction)

The engine selector suggests the best tool for each place: **Gemini Pro Extended Deep Research** for
complex or non-English-primary law if you have it (`research.gemini_available:true`), otherwise Claude's own
deep-research / web-search. There is **always** a best-available fallback — Gemini is never required. The
agent shows you the per-jurisdiction recommendation; you run it.

## 4. Generate the Deep-Research prompts

```bash
python skill/make_prompts.py
```

This fills `templates/prompt.template.md` for every *preliminary* jurisdiction that doesn't already have a
prompt, writing `data/prompts/<id>.md`. Each prompt embeds a **"What we already found (PRELIMINARY — VERIFY
and CORRECT)"** block from your current JSON, so the research engine corrects a concrete draft rather than
starting cold. It's idempotent — prompts already in `data/prompts/` or `data/prompts/done/` are never
clobbered.

## 5. Run Deep Research (HUMAN)

This is the one manual external step. Paste each `data/prompts/<id>.md` into the recommended engine (Gemini
Pro Deep Research, or Claude). Save the result and paste it back to the agent (or drop it next to the
prompt). This is the only paid/manual dependency — and it's optional in the sense that Claude's own research
is a lower-depth substitute.

## 6. Verify + AUTHOR the JSON (the heart of the loop)

The agent reads the research and writes/updates `data/jurisdictions/<id>.json`, applying:

- **The assume-a-pathway lens** — choose the *least-restrictive accurate* status. `prohibited` only when
  there is genuinely no lawful pathway; if a permit exists it's `legal_with_permit`.
- **"Silent" or "not listed" is NOT automatically `unregulated_unclear` or legal — find the default rule
  first.** Two regimes exist. In an OPEN regime (anything not prohibited is allowed) an unlisted species is
  `unregulated_unclear` or `legal`. In a CLOSED positive-list regime (only approved species are allowed) an
  unlisted species is `prohibited` by default, and often permit-ineligible. Read the statute's default clause;
  do not assume silence means freedom. And verify BOTH directions: a place can look genus-banned yet still
  lawfully permit the ordinary pet species (so the niche species may have a pathway), and a place can look
  permissive yet quietly exclude the niche species while allowing the common one (a species trap).
- **The 6-term vocabulary** — `legal` / `legal_with_permit` / `restricted` / `prohibited` /
  `unregulated_unclear` / `unknown` (use exactly these), with `confidence` (`high`/`medium`/`low`) kept
  *independent* of status.
- **Agency answers outrank Deep Research** — if a written official reply conflicts with a research finding,
  the agency wins; if the conflict looks genuine and substantive, seek confirmation before flipping.
- **Honest confidence** — no fabricated certainty; mark what's unclear as unclear.
- **OPSEC** — see [`OPSEC.md`](OPSEC.md). Keep `contacts`, `research_log`, and any `notes` internal; write
  `agency_confirmations` name-free.

Then: cite each claim into `sources[]`, append a `research_log` entry, set `verified_by`, and clear
`needs_verification`. (See [`SCHEMA.md`](SCHEMA.md) for every field.) Move the prompt to
`data/prompts/done/`.

## 7. Build → PURGE CACHE

```bash
python skill/build.py
```

This renders/updates, idempotently: the hub, the About/methodology page, the find-your-local-law self-help
finder, and one hierarchical page per jurisdiction. It sets SEO meta per `config.seo`, adds the optional
attribution footer, and **renders only public-safe fields**. It upserts by slug+parent (never cross-parent
clobber) and forces `status:publish` with comments closed.

**Then purge your host cache** — `build.py` prints this reminder. Until you do, visitors see stale pages.
See [`recipes/`](recipes/) for host-specific purge steps.

## 8. Audit for certainty

The audit is **read-only**. It lists every jurisdiction's confidence/verification gaps — what's still
preliminary, low-confidence, or `unknown` — and flags where a clarifying agency inquiry would help. Use it
to decide where to spend effort next, and (if inquiries are enabled) which places to write to.

## 9. (Optional) Inquiries — close the gaps in writing

Off by default (`inquiries.enabled:false`). Turn it on when the audit finds a clarification-worthy gap and
you have a verified contact. The flow: draft a localized inquiry per open jurisdiction → stage it → you
**confirm/edit each one** (`confirm_each` is on; nothing sends without your per-query OK) → send via your
authenticated mailbox → fetch replies (deduped by Message-ID) → record the reply → re-verify → rebuild.

Guardrails: **never invent an agency email** (verified `contacts[]` only; otherwise web form / manual); on a
bounce, find a verified replacement or flag it honestly — never guess. Requires the mailbox + SPF/DKIM/DMARC
**and MX** setup in [`EMAIL-DELIVERABILITY.md`](EMAIL-DELIVERABILITY.md); verify both directions first.

**Multiple addresses + form fallback.** If a jurisdiction lists several plausible contacts, send to all of
them (one good delivery is enough). Where a web form also exists, try email first; if there is no reply or a
confirmed bounce after about a week, reopen the inquiry as a web-form submission instead.

**Bounce triage.** A bounce means your inquiry never arrived, so do not re-send to the same address — find a
valid one or use the form. And do not re-pester a jurisdiction whose question Deep Research has since
answered; only (re)contact where a genuine agency-only gap remains.

**When a reply comes back.** Verify it, then let the agency answer **outrank Deep Research**: update the
jurisdiction's status/confidence to match, record it under `agency_confirmations` (name-free), clear
`needs_verification`, mark the inquiry answered, rebuild, and send a brief thank-you. Watch the mailbox on a
cadence so replies are not missed.

## 10. (Optional) Advocacy — where a rule is unfair or mistaken

When an activity is `prohibited`/`restricted`, or there's a species-vs-domestication anomaly, the agent
authors a **branch-aware** `advocacy.kit`: agency misreading → appeal the agency; statute → legislature;
open window → public comment. It renders bilingually (local legal language + English) with
personalize-me templates. **Sending advocacy is always your decision.**

## 11. The periodic sweep

On a cadence: process any new Deep-Research results (re-scan the results folder and batch all that are ready, so
several verify in one pass rather than one at a time); handle flagged/bounced inquiries and incoming replies;
re-verify and rebuild anything that changed; re-run the audit; act on advocacy-flag changes from new
information; **commit + back up.**

---

## The habit: commit + back up after each change

After every meaningful change — a verified jurisdiction, a build, a reply processed — commit and back up.
Laws change and you want the history; provenance lives in the JSON, so each commit is an auditable snapshot.

```bash
git add data/jurisdictions/<id>.json
git commit -m "verify <id>: <one-line what changed>"
```

> **Never commit secrets or adopter data.** `.env`, `config.json`, your `data/`, the inquiry queue, and mail
> state are all gitignored by design — keep it that way. See [`OPSEC.md`](OPSEC.md).

Back up your working copy however you normally do (e.g. a mirror copy of the repo). The committed JSON +
your backup are the recoverable source of truth; the WordPress pages are just a rendered view you can
regenerate at any time with `build.py`.

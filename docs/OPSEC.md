# OPSEC — the public / private contract

Pet Freedom is built around one clean split: **the method is public; your data and credentials are private.**
This page is the plain-terms contract for what ships, what renders, and what never leaves your machine. It's
not just a promise — most of it is enforced by how the code is structured.

> The short version: published pages show only sourced, public-safe facts. Your credentials, your working
> notes, agency contact details, and anyone's real name stay local.

---

## What ships vs what never ships

| Thing | Ships / public? |
|---|---|
| The Python toolchain, templates, starter packs (pure geography), docs | ✅ ships (this repo) |
| The small `demo/roof-rat/` worked example | ✅ ships on purpose (tutorial + funnel) |
| Status vocabulary, the assume-a-pathway lens, the advocacy-kit model | ✅ ships (it's the method) |
| **Your `.env`** (WordPress + mailbox credentials) | ❌ never — gitignored |
| **Your `config.json`** (your site URL, sender identity, preferences) | ❌ never — gitignored |
| **Your `data/jurisdictions/*.json`** (your researched content) | ❌ never committed — gitignored |
| The inquiry queue (`inquiries.json`) + mail state (`.mail_state.json`) | ❌ never — gitignored |
| Deep-Research result dumps (`*.dr.md`, `research-dumps/`) | ❌ never — gitignored |
| Any person's real name (yours, family, an official's) | ❌ never in public output |
| `contacts[]`, `research_log[]`, any `notes`, `advocacy.notes`, `advocacy.kit.confidence_notes` | ❌ never rendered to a page |

Seed data and your JSON **may** include **official government contacts** (an agency office's published email
or web form — an official acting in their official capacity) and **public sources** (statutes, agency pages).
What it must **never** include is *your* identity, address, employer, or credentials, or an official's
personal name presented as a person rather than an office.

---

## The render-only-public rule

The build (`skill/build.py`) only ever reads **public-safe fields** into a render function. The internal
fields are never passed to the page builder at all — so a leak isn't "we forgot to hide it," it's
structurally absent.

**Rendered (public):**
`summary`; the `jurisdiction` identity (name, level, parent, `local_terms`); each activity's `status`,
`confidence`, `why`, `governing_law`, `verified_date`, and `source_ids`; `restrictions[]`; `sources[]`;
`agency_confirmations[]` (name-free); and `advocacy.kit` (minus `confidence_notes`).

**Never rendered (internal):**
`contacts[]`, `research_log[]`, any `notes` (including `advocacy.notes` and `advocacy.kit.confidence_notes`).
The raw `verified_by` / `needs_verification` values are never shown either — they only *derive* the
"Preliminary" banner.

So: keep working reasoning, who-to-ask details, and provenance in the internal fields and they will never
surface on a page. Anything you'd be uncomfortable seeing published belongs in `notes` / `research_log` /
`contacts`, not in a public field.

---

## The gitignore guarantees

`.gitignore` is the second line of defense. It excludes, by construction:

- `.env` and `*.local` / `*.local.*` — credentials,
- `config.json` — your live configuration,
- `/data/` and `data/jurisdictions/*.json` / `data/prompts/*.md` — your content and prompts
  (`.gitkeep` files are kept so the folders exist),
- `inquiries.json`, `.mail_state.json`, `mailstate/` — the inquiry queue and mailbox state (real addresses,
  reply text, Message-IDs),
- `*.dr.md`, `research-dumps/` — raw Deep-Research dumps,
- `__pycache__/`, `*.pyc`, OS cruft.

The only species data that ships is the committed `demo/roof-rat/` sample. **Before pushing, double-check
`git status` shows none of the above** — if you renamed a data file out of `data/`, it may slip the ignore
rules.

---

## The opt-in name scrubber

`common.naturalize()` is a belt-and-suspenders scrubber: give it a `{name: replacement}` map and it rewrites
those names to neutral placeholders in any text. It's **opt-in and empty by default** — the name list is
*your own*, so no real person's name is hard-coded anywhere in the skill. Use it if you want a backstop
against a stray name in free text (e.g. an agency reply you're quoting). It is a safety net, not a substitute
for the render-only-public rule.

The same discipline applies to `verified_by`: use neutral values (`maintainer`, `agency`, `gemini-dr`, …) —
never a real person's name.

---

## The rule about names and contacts (read this once)

- **Official government contacts are OK in seed/JSON data.** An agency's published office email or web form
  is a public, official channel — store it in `contacts[]` (internal) so the inquiry module can use it.
- **Public sources are OK.** Statutes, regulations, agency pages — that's the whole point; cite them in
  `sources[]`.
- **The adopter's identity and credentials are NEVER in the data or in public output.** Your name, address,
  neighborhood, employer, family, and WordPress/mailbox credentials live in `.env`/`config.json` only, and
  even your sender name (if you enable inquiries) stays in your local `config.json`, never in the repo.
- **An official's personal name does not belong on a public page.** Capture what an agency *confirmed* in a
  name-free `agency_confirmations[]` line; keep the raw reply and the person's name in the internal inquiry
  queue.

If you're ever unsure whether something is safe to publish, the test is simple: *would this expose a private
person, or a credential?* If yes, it's internal.

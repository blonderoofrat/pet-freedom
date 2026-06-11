# SCHEMA — the jurisdiction data model

One JSON file per place lives in `data/jurisdictions/<id>.json`. That file is the **single source of
truth** for everything the build publishes about that jurisdiction. Add a place = add a file and rerun
`skill/build.py`; no code changes, ever.

This is deliberately a plain, versionable, diff-able file (not a database row) so:

- you can see history when a law changes,
- the agent can author and verify it directly,
- it's portable if you ever move off WordPress, and
- every published claim traces back to a cited source recorded *inside* the file.

> **Honesty rule, baked into the schema.** Status and confidence are separate. You can be *highly
> confident* that a rule is *unclear*. Never fabricate certainty. This is a research aid, not legal
> advice.

---

## Top-level shape

```jsonc
{
  "jurisdiction": { /* identity + hierarchy — see below */ },
  "summary": "One plain sentence a human (and a search snippet) can read.",
  "last_reviewed": "2026-06-11",
  "advocacy": { "flag": false, "notes": "", "kit": { /* optional, PUBLIC — see below */ } },

  "activities": {
    "keep":      { /* ActivityRecord */ },
    "breed":     { /* ActivityRecord */ },
    "sell_give": { /* ActivityRecord */ },
    "transport": { /* ActivityRecord */ }
  },

  "restrictions": [ /* RestrictionRecord, ... */ ],

  "sources":               [ /* every claim traces to one of these — PUBLIC */ ],
  "contacts":              [ /* agencies to ASK when something is open — INTERNAL, never rendered */ ],
  "agency_confirmations":  [ "Plain, name-free sentences an agency confirmed in writing — PUBLIC" ],
  "research_log":          [ /* dated provenance — INTERNAL, never rendered */ ]
}
```

The activity keys come from `config.json` (`activities`), defaulting to
`keep` / `breed` / `sell_give` / `transport`. If you add a custom activity key, the build title-cases it
into a readable label automatically.

---

## `jurisdiction` block

```jsonc
"jurisdiction": {
  "id": "us-fl",            // == the URL slug segment; must be unique across all files
  "level": "country | state | province | territory | municipality",
  "name": "Florida",        // display name
  "parent": "us",           // id of the parent jurisdiction, or null for a top-level country
  "country": "US",          // ISO2 country code
  "iso": "US-FL",           // ISO 3166 code where one exists ("" if not)
  "language": "en",         // primary language code (drives inquiry/advocacy language)
  "slug": "florida",        // optional; defaults to the id
  "local_terms": ["Felis catus", "domestic cat", "house cat"]  // search/legal terms for this place
}
```

- `id` doubles as the URL slug and as the filename (`<id>.json`).
- `parent` builds the hierarchy: a child page nests under its parent's page
  (`/<hub>/<country>/<state>/`). The build resolves parents first so the tree always renders.
- `local_terms` seeds search hints and the localized terms shown on the page. The seeder fills a sensible
  default from your configured species names (Latin + common, plus the counterpart's Latin if you set one).

---

## Status vocabulary (the six — use EXACTLY these keys)

| key | meaning | page label |
|---|---|---|
| `legal` | allowed, no special permit | Legal |
| `legal_with_permit` | allowed but needs a permit / license / registration | Legal with a permit |
| `restricted` | allowed only under specific conditions or limits | Restricted |
| `prohibited` | not allowed | Prohibited |
| `unregulated_unclear` | no rule found, or the law is silent / ambiguous | Unregulated / unclear |
| `unknown` | not yet researched | Not yet researched |

**`confidence`** is one of `high` | `medium` | `low`, and is **independent of status**. A rule can be
`unregulated_unclear` with `high` confidence (you are sure no clear rule exists) — that's not a
contradiction, it's honesty.

### The assume-a-pathway lens

When you author a status, choose the **least-restrictive status that is still accurate**. Use
`prohibited` **only** when there is genuinely no lawful pathway — not merely because a pathway is hard,
unusual, or undocumented. If a permit exists, it's `legal_with_permit`, not `prohibited`. If the law is
silent, it's `unregulated_unclear`, not `prohibited`. This keeps the resource honest and surfaces the real,
narrowest lever for the advocacy layer.

---

## ActivityRecord

One per activity under `activities`:

```jsonc
{
  "status": "legal | legal_with_permit | restricted | prohibited | unregulated_unclear | unknown",
  "confidence": "high | medium | low",
  "why": "Plain-language reason, quoting or paraphrasing the operative law. PUBLIC.",
  "governing_law": "The statute / rule / agency category, e.g. 'State Admin Code 68A-6'. PUBLIC.",
  "source_ids": ["agency-pets"],   // references into sources[]
  "verified_date": "2026-06-11",
  "verified_by": "web-research | gemini-dr | claude-deep-research | agency | maintainer",
  "needs_verification": true,      // true until it has passed the research + verify loop
  "notes": ""                      // INTERNAL working notes — NEVER rendered
}
```

**`verified_by` values** and what they mean for publishing:

| value | meaning |
|---|---|
| `web-research` | a preliminary best-guess web pass — renders a "preliminary" banner |
| `claude-deep-research` / `gemini-dr` | confirmed against official sources via Deep Research |
| `agency` | confirmed by a written agency answer (the highest authority — see below) |
| `maintainer` | you authored/confirmed it yourself |

> Don't write a real person's name into `verified_by`. Use the neutral values above.

**Agency answers outrank Deep Research.** If an official written reply conflicts with a research finding,
the agency wins — but if the conflict looks genuine and substantive, seek confirmation before flipping the
status.

---

## RestrictionRecord

The conditions/steps that attach to an activity (this becomes the reader's checklist):

```jsonc
{
  "type": "registration | license | permit | testing | health_cert | facility | inspection | other",
  "applies_to": "person | animal | both",
  "activity": ["keep", "sell_give"],     // which activities trigger it
  "summary": "What it is, in one line. PUBLIC.",
  "steps": ["Step one", "Step two"],     // rendered as a checklist
  "forms": [ { "name": "Form 1A", "url": "https://example.com/form" } ],  // or plain strings
  "where_to_file": "Where to submit it.",
  "fees": "Any fees.",
  "source_ids": ["agency-pets"]
}
```

---

## `sources` (PUBLIC — every claim links here)

```jsonc
{
  "id": "agency-pets",                       // referenced by source_ids[] elsewhere
  "title": "Captive Wildlife — Pet Rules",
  "url": "https://example.gov/captive-wildlife",
  "authority": "State Wildlife Commission",  // who publishes it (shown as the link text)
  "accessed": "2026-06-11"
}
```

Every status and restriction should point at a source. The page links each source so readers can read the
law themselves.

---

## `contacts` (INTERNAL — never rendered)

The agencies you would *ask* when a question is open. This feeds the optional inquiry module and is **never
put on a page**.

```jsonc
{
  "agency": "State Wildlife Commission — Captive Wildlife Office",
  "role": "wildlife",                 // wildlife | agriculture | customs | local | other
  "email": "",                        // only a VERIFIED address; leave blank if unknown
  "form_url": "https://example.gov/contact",
  "phone": "",
  "mailing": "",
  "primary": true,                    // which contact the inquiry uses first
  "notes": ""
}
```

> **Never invent an email.** Inquiries only ever go to a verified address from `contacts[]`. No address →
> use the web form, or handle it manually.

---

## `agency_confirmations` (PUBLIC — but name-free)

Short, plain sentences capturing what an agency confirmed in writing. These **do** render (in a "Confirmed
by the agencies" callout) — so write them name-free. The raw reply text and the official's name live in the
internal inquiry queue, never here.

```jsonc
"agency_confirmations": [
  "The state wildlife agency confirmed in writing that keeping this species as a pet needs no permit."
]
```

---

## `advocacy` (`.flag` + `.notes` internal; `.kit` PUBLIC)

```jsonc
"advocacy": {
  "flag": true,                 // set true when prohibited/restricted, or an unequal-treatment anomaly
  "notes": "INTERNAL reasoning — NEVER rendered.",
  "kit": {                      // PUBLIC — rendered as a 'How to help here' toolkit
    "case_type": "agency_species_trap | clarification | prohibition_statute | public_comment_window | legislative_watch | positive_list | precedent | other",
    "problem": "What's wrong, in plain terms.",
    "ask": "The specific change you're asking for.",
    "branch_note": "WHERE the lever really is — see below.",
    "time_sensitive": "",       // e.g. an open comment window with a deadline
    "targets": [
      { "type": "agency | legislature | public_comment | court",
        "name": "Who to write to",
        "email": "official@example.gov",   // or:
        "form_url": "https://example.gov/comment",
        "why": "Why this body is the right lever." }
    ],
    "template": {
      "en": "A ready-to-personalize message in English.",
      "es": "El mismo mensaje en el idioma local."
    },
    "confidence_notes": "INTERNAL — NEVER rendered."
  }
}
```

**`branch_note` is the core insight.** Direct the reader to the right branch of government:

- a **bureaucratic misreading** of the law → appeal/clarify with the *agency*,
- the **law as written** is the barrier → the *legislature* (or a positive-list petition),
- an **open comment window** → submit a *public comment*.

Sending advocacy is always the human's decision. Inside the kit, `notes` and `confidence_notes` are
internal and never reach a page.

---

## Inheritance rule

A child (state / municipality) inherits a parent's status **only where the child is silent — and the page
must say so.** The build renders a "National law also applies… inherited only where [child] is silent"
notice and links the parent. Never silently copy a parent's answer down; always label an inherited answer
and link upward.

---

## Confidence → publish policy

| condition | what gets published |
|---|---|
| `high` / `medium` confidence **and** `verified_by` is `gemini-dr` / `claude-deep-research` / `agency` / `maintainer` | a stated answer, with the reason and source |
| `low` confidence, **or** any activity still `needs_verification:true` with `verified_by` in `{web-research, claude-websearch}` | published with a clear **"Preliminary — not yet agency-confirmed"** banner and the self-help finder made prominent |

The raw `verified_by` / `needs_verification` values are never shown to readers — only the derived
"preliminary" banner. **No fabricated certainty, ever.**

---

## Public vs internal — at a glance

| Field | Rendered on the page? |
|---|---|
| `summary` | ✅ public |
| `jurisdiction.*` (name, level, parent, local_terms) | ✅ public |
| activities: `status`, `confidence`, `why`, `governing_law`, `verified_date`, `source_ids` | ✅ public |
| activities: `verified_by`, `needs_verification` | ⚙️ used only to derive the banner — never shown raw |
| activities: `notes` | ❌ **internal** |
| `restrictions[]` | ✅ public |
| `sources[]` | ✅ public |
| `agency_confirmations[]` | ✅ public (write them name-free) |
| `advocacy.kit` (minus `confidence_notes`) | ✅ public |
| `advocacy.flag`, `advocacy.notes`, `advocacy.kit.confidence_notes` | ❌ **internal** |
| `contacts[]` | ❌ **internal** (feeds inquiries only) |
| `research_log[]` | ❌ **internal** |

The build is structured so internal fields are **never read into a render function** — see
[`OPSEC.md`](OPSEC.md) for the full public/private contract.

# Answer Garden — leaf‑node crowdsourcing (Phase 2 module)

**Status: designed + REFERENCE-IMPLEMENTED on the live roof-rat site (blonderoofrat.com); not yet generalized into
this skill's modules.** The core skill (research → verify → publish, with optional inquiries + advocacy) is complete
without it. This module is the next layer: crowdsourcing the **leaf nodes** — individual cities/counties — where the
law is too local and too numerous for one maintainer to research alone.

**What the live reference already has (2026-06-12) — port these when generalizing this module:**
- the per-node reader **widget** (share / request / **up-down vote + correction**) on every jurisdiction page;
- a public, **hardened intake endpoint** — honeypot + bot/origin guards + per-IP rate-limit + per-IP/locality dedupe
  + a **global daily cap on brand-new localities**, so only real users grow the tree (not agents spamming every zip);
- a wp-admin **moderation queue** (everything untrusted until a maintainer verifies it against the official source);
- a **spreading-activation router** (weighted jurisdiction graph → Dijkstra distance → expert routing → per-region
  decaying reputation), built + tested offline (reproduces the design's simulation on the real graph).

In the source project these live in `wp_tools/answergarden.py` (router + CLI), `games/wordpress-plugin/`
`roofrat-adventures.php` (the `garden-submit` / `garden` REST routes + moderation panel), and
`wp_tools/legal_build.py` (`garden_widget()`).

## The problem it solves
Country, state/province, and territory law is finite and researchable. **Municipal** ordinances (a city's exotic‑pet
or rodent rule) are effectively unbounded — tens of thousands of them. You can't (and shouldn't) Deep‑Research every
city. But readers *in* those cities can tell you what they find. The Answer Garden turns scattered reader knowledge
into verified, structured leaf nodes that hang off the existing jurisdiction tree.

## The model (spreading‑activation Answer Garden)
Based on Mark Ackerman's "answer garden" idea, adapted with a spreading‑activation twist:
1. **Growing tree.** Each published jurisdiction page carries a small intake widget ("Know your city's rule? Tell
   us / ask us"). A submission creates (or activates) a **leaf node** under the right parent (city → state → country).
2. **Spreading activation.** A question/answer at one node raises the "activation" of related nodes (same state,
   similar ordinance family), so the system surfaces likely‑relevant existing answers before asking the crowd again —
   reducing dead‑ends and duplicated effort. (Our offline simulation showed reuse rising and dead‑ends falling sharply
   once weighted edges were added.)
3. **Verification queue.** Submissions are **untrusted** until verified. They land in a moderation queue; a maintainer
   (or a trusted expert) confirms against the official source before the leaf is published — same honesty bar as the
   rest of the resource (sourced, confidence‑rated, "research aid, not legal advice").
4. **Expert routing.** Open questions can be routed to the most likely knowledgeable contributor for that branch.

## What it will port (from the source project, generalized)
- A public intake **widget** embedded on jurisdiction pages (was `garden_widget()` in the original builder) →
  POSTs to a public, rate‑limited, bot/origin‑guarded endpoint.
- Companion‑plugin routes `POST /<ns>/garden-submit` (public intake → queue) and `GET/POST /<ns>/garden` (admin
  moderate), plus a moderation panel — all under the configurable namespace, opt‑in.
- The leaf‑node schema (a lightweight jurisdiction record at `level:"municipality"`, parented to its state) so leaves
  reuse the same SCHEMA.md / build.py rendering with zero new page code.

## Build notes for whoever implements this
- Keep the **render‑only‑public** discipline: never expose a submitter's identity; store contact only with consent;
  publish only verified, sourced leaves.
- Reuse `build.py`'s hierarchy (municipality → state → country) — a verified leaf is just another jurisdiction JSON.
- Gate publishing on verification, exactly like the DR/agency loop (`needs_verification` until confirmed).
- The spreading‑activation logic can start simple (same‑parent + ordinance‑family edges) and grow.

*The original design notes and an offline activation simulation live in the source project's planning folder; this
README is the generalized, shippable summary. Contributions welcome (see ../../CONTRIBUTING.md).*

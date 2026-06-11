# Pet Freedom — build status

**v1: COMPLETE, verified, and PUBLISHED** at <https://github.com/blonderoofrat/pet-freedom> (public, MIT/CC‑BY).
Core pipeline works end‑to‑end (offline‑verified); optional modules built; a one‑click in‑browser demo ships;
one module (Answer Garden) designed for Phase 2. The canonical source stays in the private project's `pet-freedom/`
and is synced to the public release folder for pushing via GitHub Desktop.

## What's built & verified ✅
| Area | Files | Status |
|---|---|---|
| Foundation | `skill/config.py`, `skill/common.py` | compile‑clean; config‑driven |
| Publish | `skill/build.py` | **dry‑run verified: 110 pages render offline, leak‑clean HTML**; SEO (rank_math/yoast/none); attribution footer; render‑only‑public |
| Research | `skill/seed.py` (bulk seeder — the gap, now filled), `skill/make_prompts.py`, `templates/prompt.template.md`, `starter-packs/` (US + ~40 countries) | compile‑clean; tested |
| Engine/audit | `skill/engine.py` (pluggable engine recommender), `skill/audit.py` (certainty audit → suggests inquiries) | compile‑clean; tested |
| Privacy export | `skill/export_seed.py` | run on real data → produced the demo dataset; structural + name backstop |
| Reference data | `demo/roof-rat/` (107 scrubbed jurisdiction JSONs + README) | **validated: 0 private leaks; 13 agency_confirmations, 48 advocacy kits, 78 official contacts preserved** |
| Live demo | `skill/playground.py` → `demo/playground/` (`blueprint.json` + WXR, curated 26‑page + full 110‑page; `demo.config.json`) | **offline‑generated; XML well‑formed; 0 sentinel/private leaks; root‑relative nav; real funnel links** — one‑click WordPress Playground "try it live" |
| SEO no‑plugin path | `mu-plugin/register-seo-meta.php` | php‑lint clean |
| Companion plugin (optional) | `plugin/pet-freedom-companion.php` (+README) | php‑lint clean; deploy‑compatible |
| Inquiries (optional, off by default) | `skill/inquiries.py`, `skill/mail.py` | compile‑clean; tested; 17 languages; per‑query confirm; never‑invent‑email |
| Docs | `SKILL.md`, `README.md`, `docs/{INSTALL,RUNBOOK,SCHEMA,OPSEC,EMAIL-DELIVERABILITY}.md`, `CONTRIBUTING.md`, `LICENSE`(MIT)+`LICENSE-docs`(CC‑BY) | written |

OPSEC verified throughout: no owner name/credential/host/species literal in any shipped code; secrets/config/working‑data
gitignored; the page renderer never emits `contacts`/`research_log`/`notes`.

## Phase 2 (designed, not yet built)
- **Answer Garden** (`modules/answer-garden/README.md`) — spreading‑activation crowdsourcing for city/county leaf nodes.

## To finish & publish (the human steps)
1. ~~Create the public GitHub repo~~ **DONE** — published at github.com/blonderoofrat/pet-freedom.
2. **Push pending updates** via GitHub Desktop (the release folder is synced): the clean MIT `LICENSE` (badge
   fix) and the new `demo/playground/` (live demo). One commit + push.
3. *(Optional)* **Live dry run** on a scratch WordPress, or just open the in‑browser demo (no setup).
4. *(Optional)* Submit the companion plugin to the WordPress.org directory (see `plugin/WORDPRESS-ORG.md`).
5. Announce / link it from blonderoofrat.com (the funnel).

## Notes
- The full methodology + decisions are in the source project's `planning/pet-freedom-skill/` (METHODOLOGY, OPEN‑QUESTIONS,
  BUILD‑PLAN) and `planning/DESIGN_DECISIONS.md`.
- Default `config.example.json` is the roof‑rat configuration, so the out‑of‑the‑box experience *is* the roof‑rat
  resource — the demo, the worked example, and the funnel, all at once.

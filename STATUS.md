# Pet Freedom — build status

**v1 scaffold: COMPLETE and verified.** Core pipeline works end‑to‑end (offline‑verified); optional modules built;
one module (Answer Garden) designed for Phase 2. Develops inside the private project for now; ready to extract to its
own public GitHub repo.

## What's built & verified ✅
| Area | Files | Status |
|---|---|---|
| Foundation | `skill/config.py`, `skill/common.py` | compile‑clean; config‑driven |
| Publish | `skill/build.py` | **dry‑run verified: 110 pages render offline, leak‑clean HTML**; SEO (rank_math/yoast/none); attribution footer; render‑only‑public |
| Research | `skill/seed.py` (bulk seeder — the gap, now filled), `skill/make_prompts.py`, `templates/prompt.template.md`, `starter-packs/` (US + ~40 countries) | compile‑clean; tested |
| Engine/audit | `skill/engine.py` (pluggable engine recommender), `skill/audit.py` (certainty audit → suggests inquiries) | compile‑clean; tested |
| Privacy export | `skill/export_seed.py` | run on real data → produced the demo dataset; structural + name backstop |
| Reference data | `demo/roof-rat/` (107 scrubbed jurisdiction JSONs + README) | **validated: 0 private leaks; 13 agency_confirmations, 48 advocacy kits, 78 official contacts preserved** |
| SEO no‑plugin path | `mu-plugin/register-seo-meta.php` | php‑lint clean |
| Companion plugin (optional) | `plugin/pet-freedom-companion.php` (+README) | php‑lint clean; deploy‑compatible |
| Inquiries (optional, off by default) | `skill/inquiries.py`, `skill/mail.py` | compile‑clean; tested; 17 languages; per‑query confirm; never‑invent‑email |
| Docs | `SKILL.md`, `README.md`, `docs/{INSTALL,RUNBOOK,SCHEMA,OPSEC,EMAIL-DELIVERABILITY}.md`, `CONTRIBUTING.md`, `LICENSE`(MIT)+`LICENSE-docs`(CC‑BY) | written |

OPSEC verified throughout: no owner name/credential/host/species literal in any shipped code; secrets/config/working‑data
gitignored; the page renderer never emits `contacts`/`research_log`/`notes`.

## Phase 2 (designed, not yet built)
- **Answer Garden** (`modules/answer-garden/README.md`) — spreading‑activation crowdsourcing for city/county leaf nodes.

## To finish & publish (the human steps)
1. **Live dry run** on a scratch WordPress: `cp config.example.json config.json` (defaults to roof rat), fill `.env`,
   `cp demo/roof-rat/*.json data/jurisdictions/`, then `python skill/build.py` (start with `seo.plugin:"none"` +
   the mu‑plugin so no companion plugin is needed). Purge cache; eyeball a few pages.
2. **Create the public GitHub repo** and push the `pet-freedom/` folder (it's self‑contained and secret‑free).
   `git subtree split`/`git filter-repo` or just copy the folder into a fresh repo.
3. Announce it / link it from blonderoofrat.com (the funnel).

## Notes
- The full methodology + decisions are in the source project's `planning/pet-freedom-skill/` (METHODOLOGY, OPEN‑QUESTIONS,
  BUILD‑PLAN) and `planning/DESIGN_DECISIONS.md`.
- Default `config.example.json` is the roof‑rat configuration, so the out‑of‑the‑box experience *is* the roof‑rat
  resource — the demo, the worked example, and the funnel, all at once.

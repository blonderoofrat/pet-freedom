# 🐾 Pet Freedom

**Map a pet species' legal status across jurisdictions worldwide — and publish it as an honest, source‑cited resource. A Claude Code skill.**

Pet Freedom is a [Claude Code](https://claude.com/claude-code) skill that helps you research, verify, and publish
the legal status of an animal — **keeping, breeding, selling, and transporting** it — across countries, states, and
territories, as a structured WordPress site. It can also (optionally) close open questions by writing to the
responsible agencies, and build a branch‑aware advocacy toolkit where a rule looks unfair or mistaken.

It's **species‑agnostic** (you set the species in one config file) and **privacy‑preserving** (your credentials and
private notes never leave your machine; published pages render only public‑safe fields by design).

> A gift from the **roof‑rat community** at [blonderoofrat.com](https://blonderoofrat.com). We built this to map the
> law for our own unusual companion animal; it generalizes to any species, so we're sharing it for everyone who
> loves an animal the law hasn't caught up with yet.

## ▶ Try it live (no install)
Boot a real WordPress in your browser, preloaded with the worldwide roof‑rat resource, and click through it as
a visitor would — **[open the live demo](https://playground.wordpress.net/?blueprint-url=https://raw.githubusercontent.com/blonderoofrat/pet-freedom/main/demo/playground/blueprint.json)** (runs on [WordPress Playground](https://wordpress.github.io/wordpress-playground/); takes a few seconds to build). It's the exact output this skill publishes. More, and how to make one for your own species: [`demo/playground/`](demo/playground/).

## What you need
- **Claude Code**
- A **WordPress** site (a user with publish rights + an Application Password); **Rank Math** or **Yoast** for SEO
  (or use the bundled no‑plugin fallback)
- *(optional)* an email account on your domain — only if you want to send agency inquiries
- *(optional)* **Gemini Pro** Deep Research — otherwise Claude's own research is the fallback

## Quickstart
1. `cp config.example.json config.json` and edit it (species, site, preferences).
2. `cp .env.example .env` and fill in your WordPress (and optional mail) credentials. **Never commit `.env`.**
3. Open the project in Claude Code and ask it to *"research the legal status of <your species> and build the
   resource."* The `pet-freedom` skill takes it from there — see `SKILL.md`.

Full setup in [`docs/INSTALL.md`](docs/INSTALL.md); day‑to‑day use in [`docs/RUNBOOK.md`](docs/RUNBOOK.md); the
privacy contract in [`docs/OPSEC.md`](docs/OPSEC.md).

## Honesty & responsibility
This is a **research aid, not legal advice.** Laws change and are interpreted by local officials. Every page tells
readers to verify with the authority and read the source themselves. If you publish information produced with this
tool, **you** are responsible for its accuracy and for following your local laws. Be honest about confidence; never
fabricate certainty; never impersonate an official.

## License
Code: **MIT** (`LICENSE`). Docs & templates: **CC BY 4.0** (`LICENSE-docs`).

---
*Status: in active development (scaffolding). See `planning/` notes in the source project for the methodology and
build plan.*

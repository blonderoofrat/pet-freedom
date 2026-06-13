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

Or see **the real, live resource** it produces, in production — **[Are Roof Rats Legal? — worldwide roof‑rat laws](https://blonderoofrat.com/roof-rat-laws/)** (100+ jurisdictions, maintained and search‑indexed). The Playground link is the sandbox to *try*; this is the finished thing in the wild.

## What you need
- **Claude Code**
- A **WordPress** site (a user with publish rights + an Application Password); **Rank Math** or **Yoast** for SEO
  (or use the bundled no‑plugin fallback)
- *(optional)* an email account on your domain — only if you want to send agency inquiries
- *(optional)* **Gemini Pro** Deep Research — otherwise Claude's own research is the fallback

## 🤖 The easy way: let Claude set it up for you
Don't want to do it by hand? Open this folder in **Claude Code** and paste this — it walks you through the whole
setup (including the parts you have to do yourself) and troubleshoots as you go:

```text
I want to use the Pet Freedom skill to research and publish the legal status of [SPECIES] as a pet on my
WordPress site, and I'd like you to walk me through the whole setup and handle as much as you can.

Please: (1) make sure I have the skill and read its README, SKILL.md, and docs/INSTALL.md; (2) walk me through
filling in config.json and .env, including exactly how to create a WordPress Application Password; (3) tell me
whether I need the companion plugin or the bundled mu-plugin SEO fallback, and guide me through it; (4) seed a
few jurisdictions, run the research and verification, and publish the pages.

For any step I must do by hand (accounts, installing a plugin, purging cache), give me clear numbered
instructions and wait for me to confirm each one before moving on. If anything errors or looks wrong, diagnose
it with me. Once setup is done, take over the research-and-publish work.
```

## Quickstart (manual)
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
*Status: **v1 — complete, verified, and published.** The skill researches, verifies, and publishes a full
multi‑jurisdiction resource end‑to‑end; the [live demo](#-try-it-live-no-install) above and a
[real production site](https://blonderoofrat.com/roof-rat-laws/) (110+ jurisdictions) show exactly what it
produces. Actively maintained — issues and contributions welcome (see [`CONTRIBUTING.md`](CONTRIBUTING.md)).*

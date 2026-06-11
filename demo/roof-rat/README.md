# Demo & reference dataset — Roof Rat (*Rattus rattus*)

This folder is a **complete, real, worked example**: the legal status of the roof rat (*Rattus rattus*) as a pet
across 100+ jurisdictions — the dataset that powers **[blonderoofrat.com/roof-rat-laws](https://blonderoofrat.com/roof-rat-laws/)**,
exported here as public seed.

It serves three purposes:
1. **A tutorial** — see exactly what verified jurisdiction JSON looks like (statuses, sourced `why`, official
   `agency_confirmations`, advocacy kits, official contacts).
2. **A head start for any species** — the official **contacts** and "which agency governs what" are largely
   *species‑agnostic*. If you're researching a different animal in, say, Texas or Germany, you inherit the verified
   agency contacts and structure instead of rediscovering them. (Re‑verify the species‑specific facts for *your*
   animal.)
3. **A gift** — so the community doesn't duplicate this research or re‑email agencies about already‑answered
   questions.

## What's here (and what isn't)
Each `<id>.json` is a **scrubbed public export**: it keeps the jurisdiction facts, statuses, sourced reasoning,
official `agency_confirmations`, public `advocacy.kit`s, source citations, and **official government contact points**
(offices, official emails/forms/phones — government employees acting in their official capacity). It does **not**
contain any private maintainer data, internal process notes, or `research_log` — those never leave the source
project (see `../../docs/OPSEC.md`).

## To reproduce the roof‑rat resource on your own WordPress site
```bash
cp ../../config.example.json ../../config.json   # already defaults to the roof rat
cp demo/roof-rat/*.json ../../data/jurisdictions/  # use this dataset as your working data
# edit ../../.env with your WordPress credentials, then:
python ../../skill/build.py
```

## Honesty
Laws change and are interpreted by local officials. This is a **research aid, not legal advice** — re‑verify any
entry against the official source before relying on it. `last_reviewed` dates tell you how fresh each entry is.

*Maintained by the Blonde Roof Rat project — [blonderoofrat.com](https://blonderoofrat.com).*

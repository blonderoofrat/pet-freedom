# Starter packs

Starter packs are plain lists of **public geography** — the jurisdictions you want this resource to eventually
cover. They are the input to the bulk seeder (`skill/seed.py`), which turns each entry into a skeleton
`data/jurisdictions/<id>.json` ready for the research/verify loop to fill in.

A pack is a JSON array of entries. Each entry is just where a place is in the hierarchy — **no legal data, no
species, no personal information**:

```json
{ "id": "us-tx", "level": "state", "parent": "us", "name": "Texas",
  "slug": "texas", "country": "US", "language": "en" }
```

| field      | meaning                                                                 |
|------------|-------------------------------------------------------------------------|
| `id`       | URL slug + filename stem. Country = ISO-ish (`gb`, `jp`); sub-national = `us-tx`, `ca-on`. |
| `level`    | `country` \| `state` \| `province` \| `territory` \| `municipality`     |
| `parent`   | the `id` of the enclosing jurisdiction, or `null` for a top-level country |
| `name`     | display name                                                            |
| `slug`     | URL segment (defaults to `id` if omitted)                               |
| `country`  | ISO2 country code (e.g. `US`, `GB`)                                     |
| `language` | primary language code for local-term searches (e.g. `en`, `ja`, `es`)   |

## The two bundled packs

### `us-states.json`
The U.S. federal parent (`us`) + all 50 states + the District of Columbia + the 5 inhabited U.S. territories
(American Samoa, Guam, Northern Mariana Islands, Puerto Rico, U.S. Virgin Islands). 57 entries. This is the
"do the whole United States properly" pack — sub-national rules are where most of the interesting variation
lives, and inheritance from the `us` parent fills the silent gaps.

### `world-major.json`
~40 countries chosen by **best judgement** for broad, culture-weighted coverage of places where keeping an
unusual companion animal is plausible. This mirrors the approach the original roof-rat project used: rather
than trying to be exhaustive (every country on Earth), it weights toward the cultures and legal traditions
most likely to have hobbyists, pet communities, and a workable keep/breed/sell/transport pathway —

- **Anglosphere:** US, Canada, UK, Ireland, Australia, New Zealand, Singapore, South Africa
- **Western Europe:** France, Germany, Netherlands, Belgium, Switzerland, Austria, Spain, Portugal, Italy
- **Nordics:** Sweden, Norway, Denmark, Finland, Iceland
- **Central/Eastern & Southern Europe:** Poland, Czech Republic, Hungary, Greece, Romania
- **East Asia:** Japan, South Korea, Taiwan, Hong Kong
- **Latin America:** Mexico, Brazil, Argentina, Chile, Colombia
- **Other notable markets:** Israel, United Arab Emirates, India, Philippines

It is deliberately **not** exhaustive. It's a sensible starting frontier; trim or extend it freely.

> Both packs include the `us` country entry. The seeder de-dupes by `id` within a single run, so
> `--pack us-states world-major` creates `us` only once.

## How to trim or extend

It's just JSON — edit it and re-run the seeder. Nothing is destructive: the seeder only writes skeletons for
ids that are missing or still preliminary, and it **never** overwrites a file that already holds verified data.

1. **Add a place:** append an entry to the relevant pack (or make a new pack file, e.g. `ca-provinces.json`).
2. **Remove a place:** delete its entry. (This does not delete any already-seeded file in `data/`; remove
   that by hand if you want it gone.)
3. **Re-seed:**

   ```bash
   python skill/seed.py --pack us-states world-major
   ```

   It prints created / skipped counts. Run it again any time you grow a pack — already-seeded and
   already-verified jurisdictions are left alone.

4. **One-off, no pack:** add a single jurisdiction directly:

   ```bash
   python skill/seed.py --add ca-on --level province --parent ca --name "Ontario" \
       --slug ontario --country CA --language en
   ```

## Making your own pack for another species/region

The packs are pure geography, so they're reusable as-is for *any* species this skill is configured for — the
species and local search terms come from `config.json`, not the pack. To focus a different region (say, all
Canadian provinces + territories, or every EU member state), copy one of these files, swap in the entries you
want, and seed it.

# INSTALL — minimum reproducible setup

This is the smallest path to a working install. The **core** (research → verify → publish) needs only a
WordPress site, a publish-capable user, an Application Password, and a way to write SEO meta. Email and the
companion plugin are **optional** and you can add them later.

> **A research aid, not legal advice.** Whatever you publish, you own its accuracy. Be honest about
> confidence; never fabricate certainty; never impersonate an official.

## Get the skill (and keep it current)

Clone the repo into your own project and open it in Claude Code:

```bash
git clone https://github.com/blonderoofrat/pet-freedom
```

Clone it (rather than downloading the .zip) so the skill can update itself. When you use it, Claude checks
GitHub and, with your OK, pulls the latest and runs a self-test first: a non-breaking update applies once the
self-test passes, a breaking one pauses for confirmation. Your `config.json` and `data/` are gitignored, so an
update never overwrites your content. Manual equivalents: `python skill/update.py` (check),
`python skill/update.py --apply` (pull a non-breaking update with the self-test gate), `python skill/selftest.py`
(verify the offline pipeline any time).

## At a glance — what an adopter needs

| Requirement | When | Why |
|---|---|---|
| WordPress + a user with **publish** rights + an **Application Password** | always | the build publishes pages via core WP REST |
| **Rank Math** *or* **Yoast**, **or** the bundled `mu-plugin/register-seo-meta.php` | always | so the build can write SEO title/description/keyword/canonical |
| **Purge your host cache after every build** | always | caches hide your changes from visitors |
| Optional **companion plugin** | if `plugin.use:true` | a friendly admin page + one `/meta` SEO-meta route |
| Authenticated mailbox **+ SPF/DKIM/DMARC** on your sending domain | only for inquiries | strict receivers bounce mail that isn't authenticated |
| **Gemini Pro** Deep Research | optional | deeper research; Claude's own research is the fallback |
| Python 3.8+ | always | runs the skill scripts (stdlib only — no `pip install`) |

---

## (a) WordPress: a publish user + an Application Password

1. You need a WordPress site you control and an account on it with **publish** capability
   (Editor or Administrator).
2. In WordPress, go to **Users → Profile → Application Passwords**. Enter a name (e.g. `pet-freedom`) and
   click **Add New Application Password**.
3. Copy the generated password. WordPress shows it in space-separated groups
   (`abcd efgh ijkl …`) — the spaces are cosmetic and the skill strips them, so paste it either way.
4. Application Passwords use HTTP Basic auth; your site must be served over **HTTPS** for this to work.

> If the REST API or Application Passwords are disabled (some hosts/security plugins do this), re-enable
> them, or the build can't talk to your site.

## (b) SEO meta — pick ONE

The build writes SEO meta (title, description, focus keyword, canonical URL). Choose how it gets stored,
then set `seo.plugin` in `config.json`:

- **Rank Math** — install & activate it. Set `"seo": { "plugin": "rank_math" }`.
- **Yoast** — install & activate it. Set `"seo": { "plugin": "yoast" }`.
- **No SEO plugin** — copy the bundled fallback into your site's `mu-plugins` folder and set
  `"seo": { "plugin": "none" }`:

  ```bash
  # on your server, create the folder if needed and drop the file in:
  #   wp-content/mu-plugins/register-seo-meta.php
  ```

  `mu-plugin/register-seo-meta.php` registers the Rank Math and Yoast meta keys with `show_in_rest`, so the
  build can write them through core WP REST without any SEO plugin installed. (Must-use plugins load
  automatically — there's nothing to activate.)

## (c) Companion plugin (OPTIONAL — only when `plugin.use:true`)

The skill publishes fine **without** any custom plugin. The optional companion plugin
(`plugin/pet-freedom-companion.php`, configurable namespace) just adds a friendly **Get Started** admin page
plus one admin-only convenience route: `/meta`, a uniform endpoint for writing SEO post-meta.

- Set `"plugin": { "use": true, "namespace": "petfreedom/v1", "option_prefix": "pf_" }` to use it.
- Set `"plugin": { "use": false }` to skip it entirely (then use option **(b)** above for SEO meta).
- Install/update it like any plugin (from the WordPress.org directory, or by uploading the `.zip`). It
  makes no outbound calls and does not modify its own files.

> The current scaffold's core scripts (`seed.py`, `make_prompts.py`, `build.py`) work with
> `plugin.use:false` + the mu-plugin SEO fallback. Start there if you want the simplest setup.

## (d) Configure: copy the examples and fill them in

```bash
cp config.example.json config.json     # your species, site, and preferences
cp .env.example .env                    # your credentials (NEVER commit this)
```

Edit **`config.json`** — at minimum:

- `species.latin` (required) and `species.common` (names people use). Add a `counterpart` only if a closely
  related species is the one people *do* commonly keep (used for the "does the 'domestic X' exemption cover
  *my* species?" analysis — omit if it doesn't apply).
- `project.hub_slug` and `project.hub_title` (the section's URL + page title).
- `site.url` (required) and your `cta_links` (care guide / extra / contact — leave blank to omit).
- `seo.plugin` to match your choice in (b).
- `plugin.use` to match (c).

Edit **`.env`** with your WordPress credentials:

```ini
WP_URL=https://example.com
WP_USERNAME=your-wp-user
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

Both files are gitignored. **Never commit `.env` or `config.json`.**

### Verify the connection

```bash
python skill/seed.py --pack us-states     # fails fast with a clear message if config/.env/WP are wrong
```

If that writes skeletons without error, your config and credentials are good. (`seed.py` reads `config.json`
and `.env` through `skill/config.py` + `skill/common.py`, which both raise helpful errors when something is
missing.)

## (e) Email for inquiries (OPTIONAL)

The agency-inquiry module is **off by default**. You only need email if you turn it on. When you do, the
single hardest setup step is deliverability: a real mailbox on your domain **plus** SPF, DKIM, and DMARC, or
strict receivers will bounce your inquiries.

Fill the mail block in `.env` (SMTP for sending, IMAP for reading replies):

```ini
SITE_MAIL_USER=you@example.com
SITE_MAIL_PASS=your-mailbox-password
SITE_SMTP_HOST=mail.example.com
SITE_SMTP_PORT=465
SITE_IMAP_HOST=mail.example.com
SITE_IMAP_PORT=993
```

Then follow **[`EMAIL-DELIVERABILITY.md`](EMAIL-DELIVERABILITY.md)** to publish SPF/DKIM/DMARC and verify
with a tool like mail-tester.com before sending anything real.

---

## After every build: purge your cache

Caches (host-level and CDN) will hide your new and updated pages from visitors. **Purge your host cache after
every build** — `build.py` reminds you when it finishes. Host-specific recipes live in
[`recipes/`](recipes/) (community-submittable).

## Next

- Day-to-day operation: **[`RUNBOOK.md`](RUNBOOK.md)**
- The data model: **[`SCHEMA.md`](SCHEMA.md)**
- The privacy contract: **[`OPSEC.md`](OPSEC.md)**

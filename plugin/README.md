# Pet Freedom Companion (optional)

A tiny, generalized WordPress plugin for the **Pet Freedom** skill. It exposes
exactly three admin-only REST helpers under your configured namespace:

| Route | Method | Purpose |
|-------|--------|---------|
| `/meta?post_id=` | GET | read all post meta |
| `/meta` | POST `{post_id, meta:{k:v}}` | write post meta (`null` value deletes a key) — this is what lets the skill set Rank Math / Yoast / core SEO meta |
| `/inspect` | GET | list active plugins + versions (deploy confirms the version bump) |
| `/plugin-update` | POST `{filename, content_b64, sha256?}` | push an upgrade into this plugin's own folder over REST |

All routes require `manage_options` (a site admin; an Application Password works
well for the deploy tool). None are public.

This is **not** the big games/garden/analytics plugin — just these helpers.

## Do you even need it?

Only install it if your `config.json` has:

```json
"plugin": { "use": true, "namespace": "petfreedom/v1", "option_prefix": "pf_" }
```

If `plugin.use` is `false`, the skill publishes through **core WP REST** plus
the bundled **mu-plugin SEO fallback** (which registers the SEO meta keys so
core REST can write them). In that mode you do not need this plugin at all.
Install it when you want one-command REST upgrades and a uniform meta endpoint.

## Keep the two constants in sync with config.json

At the top of `pet-freedom-companion.php`:

```php
define( 'PETFREEDOM_NS', 'petfreedom/v1' );  // <- config.json plugin.namespace
define( 'PETFREEDOM_OPT_PREFIX', 'pf_' );    // <- config.json plugin.option_prefix
```

These must match the `plugin.namespace` and `plugin.option_prefix` values in
your `config.json`, or the Python tooling will call routes that do not exist.
If you change the namespace in one place, change it in the other.

## Install (first time)

The very first install must go through wp-admin (the chicken-and-egg point —
the `/plugin-update` endpoint does not exist on the site yet):

1. Zip the `plugin/` folder so it contains
   `pet-freedom-companion/pet-freedom-companion.php`, **or** just copy the
   single `.php` file to
   `wp-content/plugins/pet-freedom-companion/pet-freedom-companion.php`.
2. In wp-admin go to **Plugins → Add New → Upload Plugin**, upload the zip, and
   **Activate** "Pet Freedom Companion".
3. Confirm the routes are live:
   `GET /wp-json/<your-namespace>/inspect` (returns 401 unless authenticated as
   an admin — that is correct).

## Upgrade (every time after the first)

Once the plugin is installed and active, later upgrades flow over REST — no
wp-admin upload needed. The skill's Python deploy tool reads the local `.php`,
computes its sha256, base64-encodes it, and POSTs to `/plugin-update`. The
endpoint verifies the hash, rotates a `.bak.1 … .bak.5` chain, writes the file,
and flushes the plugins cache. The new code takes effect on the **next**
request.

### ⚠️ MANDATORY: `php -l` before every deploy

A broken push that **still begins with `<?php`** passes the endpoint's opening
guard but can **fatal the whole site** once the new code loads. The endpoint
cannot catch a parse/logic error — only a syntax linter can. So **always** lint
first:

```sh
php -l pet-freedom-companion.php
# => "No syntax errors detected" before you deploy
```

If a bad version does get pushed and the site fatals, the recovery is the
backup rotation: via SFTP / your host's file manager, rename the newest backup
(`pet-freedom-companion.php.bak.1`) back over
`pet-freedom-companion.php`. The site recovers on the next request.

## OPSEC / safety notes

- Every route is admin-gated; nothing is exposed to anonymous visitors.
- `/plugin-update` is locked to a strict filename whitelist
  (`^[a-z0-9_-]+\.(php|md|txt|json|css|js)$`), runs `basename()` to defeat path
  traversal, caps writes at 256 KB, and only ever writes inside this plugin's
  own directory.
- The plugin stores no secrets and references no domain, owner, or species —
  all of that lives in your `config.json`.

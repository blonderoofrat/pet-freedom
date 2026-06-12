# Pet Freedom Companion (optional)

A tiny, generalized WordPress plugin for the **Pet Freedom** skill. It adds a friendly **Get Started** admin
page plus exactly **one** admin-only REST helper under your configured namespace:

| Route | Method | Purpose |
|-------|--------|---------|
| `/meta?post_id=` | GET | read all post meta |
| `/meta` | POST `{post_id, meta:{k:v}}` | write post meta (`null` value deletes a key) — this is what lets the skill set Rank Math / Yoast / core SEO meta |

The route requires `manage_options` (a site admin; an Application Password works well for the tooling). It is
never public. The plugin makes no outbound calls and **does not modify its own files**.

> Earlier versions (≤1.1.0) also shipped `/inspect` and a self-update (`/plugin-update`) route. Those were
> **removed in 1.2.0**: a REST endpoint that writes the plugin's own files is disallowed by the WordPress.org
> directory (plugins update *through* the directory, not by pushing code to themselves). The skill never needed
> them — it only uses `/meta`.

This is **not** the big games/garden/analytics plugin — just the Get Started page and the `/meta` helper.

## Do you even need it?

Only install it if your `config.json` has:

```json
"plugin": { "use": true, "namespace": "petfreedom/v1", "option_prefix": "pf_" }
```

If `plugin.use` is `false`, the skill publishes through **core WP REST** plus the bundled **mu-plugin SEO
fallback** (which registers the SEO meta keys so core REST can write them). In that mode you do not need this
plugin at all. Install it when you want the friendly admin page and a uniform SEO post-meta endpoint.

## Keep the two constants in sync with config.json

At the top of `pet-freedom-companion.php`:

```php
define( 'PETFREEDOM_NS', 'petfreedom/v1' );  // <- config.json plugin.namespace
define( 'PETFREEDOM_OPT_PREFIX', 'pf_' );    // <- config.json plugin.option_prefix
```

These must match the `plugin.namespace` and `plugin.option_prefix` values in your `config.json`, or the Python
tooling will call a route that does not exist. If you change the namespace in one place, change it in the other.

## Install & update

Like any normal WordPress plugin:

1. Zip the `plugin/` folder so it contains `pet-freedom-companion/pet-freedom-companion.php` (+ `readme.txt`),
   **or** copy that file to `wp-content/plugins/pet-freedom-companion/pet-freedom-companion.php`.
2. In wp-admin: **Plugins → Add New → Upload Plugin**, upload the zip, and **Activate** "Pet Freedom Companion".
   (If the plugin is published in the WordPress.org directory, you can instead search for it there.)
3. Confirm the route is live: `GET /wp-json/<your-namespace>/meta?post_id=1` returns `401` unless authenticated
   as an admin — that is correct, and means the capability gate is working.

**Updates** flow the normal way — through the WordPress.org directory (one-click), or by uploading a newer
`.zip`. The plugin never updates itself.

## OPSEC / safety notes

- The `/meta` route is admin-gated (`manage_options`); nothing is exposed to anonymous visitors.
- It sanitizes meta keys (`sanitize_key`) and only reads/writes post meta — no file writes, no remote code.
- The plugin stores no secrets and references no domain, owner, or species — all of that lives in your
  `config.json`.

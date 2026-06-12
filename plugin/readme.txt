=== Pet Freedom Companion ===
Contributors: blonderoofrat
Tags: pet, animal, legal, law, wildlife, exotic pets, rest api, seo
Requires at least: 5.8
Tested up to: 7.0
Requires PHP: 7.4
Stable tag: 1.2.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Map a pet species' legal status across jurisdictions worldwide and publish it — companion to the free Pet Freedom skill for Claude Code.

== Description ==

**Pet Freedom** helps you research, verify, and publish the legal status of an animal — whether it can be **kept, bred, sold, and transported** — across countries, states, and territories, as a structured, SEO-ready WordPress resource. It is *species-agnostic* (you set the species in one config file) and *privacy-preserving* (your credentials and private notes never leave your machine; published pages render only public-safe fields).

**See it before you install anything:** a one-click [live demo runs in your browser](https://playground.wordpress.net/?blueprint-url=https://raw.githubusercontent.com/blonderoofrat/pet-freedom/main/demo/playground/blueprint.json) (via WordPress Playground), preloaded with a worldwide example resource — no account, no server.

This plugin — **Pet Freedom Companion** — is the small WordPress half of the project. It adds:

* A friendly **Get Started** admin page that explains what Pet Freedom is, what else you need, and shows whether everything is wired up correctly.
* One optional, **admin-only** REST helper used by the publishing tool: read/write post meta, so SEO meta for **Rank Math** or **Yoast** can be set programmatically.

The route requires the `manage_options` capability — nothing is exposed to anonymous visitors. The plugin stores no secrets, references no specific domain/owner/species, makes no outbound calls, and does not modify its own files; all configuration lives in your own `config.json`.

= Do I need anything else? =

Yes. This plugin is the companion, not the engine. The actual research-and-publish work is done by **Claude Code** plus the free, open-source **Pet Freedom skill**:

* Claude Code: https://claude.com/claude-code
* The free Pet Freedom skill (and its `config.json`), distributed on GitHub: https://github.com/blonderoofrat/pet-freedom

The skill is distributed via GitHub regardless of this plugin's listing here.

= Honesty & responsibility =

This is a **research aid, not legal advice.** Laws change and are interpreted by local officials. Every published page tells readers to verify with the responsible authority and read the source themselves. If you publish information produced with this tool, **you** are responsible for its accuracy and for following your local laws.

= Open source =

* This WordPress plugin is **GPLv2 or later** (so it is compatible with the WordPress.org directory).
* The wider Pet Freedom project (the Claude Code skill, its Python tooling, and docs) is **MIT** (code) / **CC BY 4.0** (docs). See the GitHub repository.

A gift from the roof-rat community at https://blonderoofrat.com — built to map the law for one unusual companion animal, generalized so it works for any species.

== Installation ==

1. Install and activate the plugin (Plugins → Add New → search "Pet Freedom Companion", or upload the .zip via Plugins → Add New → Upload Plugin).
2. Open the new **Pet Freedom** menu item in wp-admin and read the **Get Started** page.
3. Install **Claude Code** and the free **Pet Freedom skill** from GitHub: https://github.com/blonderoofrat/pet-freedom
4. In the skill's `config.json`, keep the `plugin.namespace` and `plugin.option_prefix` values in sync with the `PETFREEDOM_NS` and `PETFREEDOM_OPT_PREFIX` constants shown on the Get Started page.
5. Create a WordPress Application Password for a user with publish rights, and give it to the skill so it can publish on your behalf.

You do not strictly need this plugin to use the skill — it can also publish through core WP REST plus a bundled SEO fallback. Install this companion when you want the friendly admin page and a uniform SEO post-meta endpoint.

== Frequently Asked Questions ==

= Can I see it in action before installing? =

Two ways. (1) A [live demo runs entirely in your browser](https://playground.wordpress.net/?blueprint-url=https://raw.githubusercontent.com/blonderoofrat/pet-freedom/main/demo/playground/blueprint.json) via WordPress Playground — no account, no server. (2) Browse the real, maintained resource this skill produces, in production: [Are Roof Rats Legal? — worldwide roof-rat laws](https://blonderoofrat.com/roof-rat-laws/) (100+ jurisdictions, search-indexed). The first is the sandbox to try; the second is the finished thing in the wild.

= How do I set it up? =

The easy way: paste a short prompt into **Claude Code** and it walks you through the whole setup — `config.json`, your Application Password, whether to use this plugin or the bundled SEO fallback, seeding, and publishing — including step-by-step help with the parts you do by hand, and troubleshooting. The exact prompt is on the plugin's **Get Started** admin page (and in the project README on GitHub). Prefer to do it manually? See `docs/INSTALL.md` in the repository.

= What does this plugin actually do on its own? =

It adds a **Get Started** info page to wp-admin and registers one optional, admin-only REST helper route (post-meta read/write). It does not publish anything by itself, collect any data, modify its own files, or expose anything to anonymous visitors.

= Do I need anything else? =

Yes — the free **Pet Freedom skill** for **Claude Code**. The skill does the research, verification, and publishing; this plugin is the small WordPress companion it talks to. Get the skill here: https://github.com/blonderoofrat/pet-freedom (Claude Code: https://claude.com/claude-code).

= Is this legal advice? =

No. It is a **research aid, not legal advice.** Always verify with the responsible authority and read the original source. You are responsible for the accuracy of anything you publish and for following your local laws.

= Does it collect or send any of my data? =

No. The plugin stores no secrets, references no specific domain/owner/species, and adds no tracking. Your credentials and private notes stay on your own machine; published pages render only public-safe fields.

= Is the REST route safe? =

Yes. The single `/meta` route requires the `manage_options` capability (a site administrator, e.g. via an Application Password) and is never exposed to anonymous visitors. It sanitizes meta keys and only reads/writes post meta. The plugin contains no file-writing or self-update code and makes no outbound calls.

= Which SEO plugins are supported? =

Rank Math and Yoast (via the generic post-meta route), or a no-plugin fallback shipped with the skill. You choose in the skill's `config.json`.

= Where do I report issues or get the source? =

GitHub: https://github.com/blonderoofrat/pet-freedom — issues, source, and the skill itself live there. Project home: https://blonderoofrat.com

== Screenshots ==

1. The Pet Freedom "Get Started" admin page: what the project is, what you also need (Claude Code + the free skill), live route status, and the two config constants to keep in sync.

== Changelog ==

= 1.2.0 =
* Removed the `/inspect` and self-update (`/plugin-update`) REST routes for WordPress.org directory compliance and to keep the plugin minimal. It now exposes only the admin-only `/meta` route the skill needs; updates flow through the directory (or a re-uploaded .zip), and the plugin never modifies its own files.
* Added a one-click "see it live in your browser" WordPress Playground demo link to the Get Started page and readme.
* Updated the Get Started page and docs to match.

= 1.1.0 =
* Added a user-facing **Get Started** admin page (top-level "Pet Freedom" menu) explaining the project, what else is needed, live REST-route status, and the config constants.
* Relicensed the plugin to **GPLv2 or later** for WordPress.org directory compatibility (the wider project remains MIT / CC BY 4.0).
* Added plugin headers (Plugin URI, Author, License URI, Requires at least, Requires PHP) and discovery links to GitHub and blonderoofrat.com.
* No new write routes and no data collection — the new page is read-only/info-only.

= 1.0.0 =
* Initial release: admin-only REST helpers — generic post-meta read/write (Rank Math / Yoast SEO meta), install inspect, and an admin-authenticated self-update endpoint.

== Upgrade Notice ==

= 1.2.0 =
Removes the self-update and inspect REST routes for WordPress.org compliance; only the admin-only post-meta route remains. No change to how the skill publishes (it uses /meta).

= 1.1.0 =
Adds a friendly Get Started admin page and relicenses to GPLv2-or-later for the WordPress.org directory. No breaking changes; existing REST routes are unchanged.

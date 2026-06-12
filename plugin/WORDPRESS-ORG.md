# Submitting Pet Freedom Companion to the WordPress.org plugin directory

A short, non-programmer guide. The goal is a **public, searchable page** on
WordPress.org so that people looking for a way to map an animal's legal status
can *discover* the plugin — and from there, the free **Pet Freedom skill** for
Claude Code.

> **You do not have to do this.** The skill is distributed on GitHub regardless,
> and the plugin works whether or not it is in the WP.org directory. A WP.org
> listing is purely a free discovery channel. Approval is **not guaranteed**.

## What you get if it's approved

- A public page at `https://wordpress.org/plugins/pet-freedom-companion/`.
- Searchability inside every WordPress admin (Plugins → Add New).
- One-click install/update for users.
- SVN access to publish future versions (WP.org hosts releases in SVN, not Git).

## Step-by-step

1. **Create a free WordPress.org account** at https://login.wordpress.org/register
   (this is the account you'll submit and later manage the plugin with). Set the
   account username as the `Contributors:` value in `readme.txt` (currently a
   placeholder, `petfreedom`).
2. **Make a clean .zip** containing a single folder named `pet-freedom-companion`
   with the plugin files inside it:
   ```
   pet-freedom-companion/
     pet-freedom-companion.php
     readme.txt
   ```
   (`README.md` and this file can be included but are not required by the
   directory; `readme.txt` is the one WP.org parses for the listing.)
3. **Submit the .zip** at https://wordpress.org/plugins/developers/add/ — upload
   it and confirm. There is a one-time automated check plus a manual review.
4. **The review.** A volunteer from the Plugin Review Team reads the code and
   emails you. They may ask questions or request small changes (common ones:
   prefix functions/options — we already use `pet_freedom_` / `PETFREEDOM_` /
   `pf_`; escape all output — we use `esc_url`/`esc_html`; no calling home — we
   don't). Reply, make any asked-for edits, and they re-review.
5. **Approval → SVN.** Once approved you get a Subversion repository. You commit
   the plugin into `trunk/`, then tag a release (e.g. `tags/1.1.0/`), and set
   `Stable tag:` in `readme.txt` to that version. WP.org builds the public page
   from there. (If SVN is unfamiliar, this is the one genuinely technical step —
   ask Claude Code to walk you through the `svn` commands when you reach it.)

## Directory guidelines to keep in mind

The full guidelines: https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/

The ones that matter for this plugin:

- **Must be GPL-compatible.** ✅ The plugin is licensed **GPLv2 or later** (header
  + `readme.txt`). The wider project is MIT / CC BY 4.0, which is also fine — the
  plugin's own license is what the directory checks.
- **Must provide user value on its own.** ✅ The **Get Started** admin page gives
  the plugin standalone, human-facing value (it isn't pure REST plumbing). This
  was the specific reason a bare helper plugin would be rejected.
- **No aggressive promotion / "powered by" spam / upsells.** ✅ We mention the
  required companion (Claude Code + the skill) and link GitHub + the project home
  once, on the info page and in the readme — that's allowed because it's
  necessary context, not advertising. Don't add nag banners, affiliate links, or
  paid upsells.
- **No self-modifying code / no tracking / no calling home / no obfuscation.** ✅ As of **v1.2.0** the plugin
  exposes only the admin-only `/meta` route. The earlier self-update (`/plugin-update`) and `/inspect` routes
  were **removed**: a REST endpoint that writes the plugin's own files is disallowed by the directory (plugins
  update *through* WordPress.org, not by pushing code to themselves), and it would have triggered a rejection.
  The plugin collects no data and makes no outbound calls. Keep it that way.
- **All output escaped, all input sanitized, capability checks on every route.**
  ✅ Already done (`manage_options`, `esc_*`, `sanitize_key`, filename whitelist).
- **Trademarks:** don't imply official endorsement by WordPress, Anthropic, etc.
  "for Claude Code" as a compatibility statement is fine; "official" is not.

## If WP.org rejects it (the fallback)

A rejection is not the end — it just means no `wordpress.org/plugins/...` page.
You still have two good distribution paths, and the **skill is on GitHub either
way**:

1. **GitHub Releases.** Attach the `pet-freedom-companion.zip` to a GitHub release
   on the repo. Users download it and install via
   Plugins → Add New → Upload Plugin. Link it from the README.
2. **blonderoofrat.com.** Host the same `.zip` for direct download and link it
   from the project page as the "WordPress companion" download.

Either way, the **Get Started** page, the README, and `blonderoofrat.com` point
people to the free Pet Freedom skill — the discovery funnel works with or without
the directory listing.

## Quick pre-submission checklist

- [ ] `readme.txt` `Stable tag:` matches the version in the plugin header (**1.2.0**).
- [ ] GitHub URL is set to `https://github.com/blonderoofrat/pet-freedom` (already done in the
      plugin header `PETFREEDOM_GITHUB` constant and in `readme.txt`). Confirm the repo is public.
- [ ] `Contributors:` is set to `blonderoofrat` — confirm that's also your **WordPress.org**
      username when you register at wordpress.org (GitHub and WP.org accounts are separate; use the
      same handle for consistency, or update this line to match your actual WP.org username).
- [ ] Run `php -l pet-freedom-companion.php` → "No syntax errors detected."
- [ ] Zip with the folder name `pet-freedom-companion/` at the top level.
- [ ] Add at least one screenshot of the Get Started page (lowercase **`screenshot-1.png`**) if you want the
      Screenshots section to render on the public page (added at the SVN/`assets` step, not in the plugin zip).
      Capture it either by (a) temporarily uploading the `.zip` to any WordPress and opening **Pet Freedom →
      Get Started**, or (b) the **admin-preview Playground link** (boots straight to the Get Started page with a
      neutral URL): `https://playground.wordpress.net/?blueprint-url=https://raw.githubusercontent.com/blonderoofrat/pet-freedom/main/demo/playground/blueprint-admin.json`

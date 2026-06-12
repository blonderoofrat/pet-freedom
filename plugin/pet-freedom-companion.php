<?php
/**
 * Plugin Name: Pet Freedom Companion
 * Plugin URI:  https://github.com/blonderoofrat/pet-freedom
 * Description: Companion for the free Pet Freedom skill for Claude Code: map a pet species' legal status across jurisdictions worldwide and publish it as a sourced WordPress resource. Adds a friendly admin "Get Started" page plus one optional, admin-only REST helper for writing SEO post-meta (Rank Math / Yoast). Research aid, not legal advice.
 * Version:     1.2.0
 * Author:      Pet Freedom (blonderoofrat.com)
 * Author URI:  https://blonderoofrat.com
 * License:     GPLv2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Requires at least: 5.8
 * Requires PHP: 7.4
 * Text Domain: pet-freedom-companion
 *
 * LICENSE NOTE: This WordPress plugin is licensed GPLv2-or-later so it is
 * compatible with the WordPress.org plugin directory. The wider Pet Freedom
 * project (the Claude Code skill, its Python tooling, and docs) is licensed
 * MIT (code) / CC BY 4.0 (docs) — see the GitHub repository.
 *
 * This is the SMALL, generalized companion — NOT a big games/garden plugin.
 * It implements exactly one REST concern — generic post-meta read/write, used
 * by the skill to set SEO meta — plus an info-only admin page. Everything
 * species-/site-specific lives in your skill's config.json; nothing here
 * references any domain, owner, or species.
 *
 * Install: place this folder at wp-content/plugins/pet-freedom-companion/
 * then activate "Pet Freedom Companion" on the wp-admin Plugins screen.
 * Updates flow through the WordPress.org directory (or, if you installed the
 * .zip manually, by uploading a newer .zip) — the plugin never modifies itself.
 *
 * Pairs with: Claude Code (https://claude.com/claude-code) + the free
 * Pet Freedom skill, distributed on GitHub (see PETFREEDOM_GITHUB below).
 */

if ( ! defined( 'ABSPATH' ) ) { exit; }

/* ======================================================================
 * CONFIG — EDIT THESE TWO TO MATCH config.json.
 * Keep them in sync with the skill's config.json `plugin` block:
 *   PETFREEDOM_NS         <-  plugin.namespace      (default "petfreedom/v1")
 *   PETFREEDOM_OPT_PREFIX <-  plugin.option_prefix  (default "pf_")
 * The namespace is the REST route prefix (/wp-json/<namespace>/...). The
 * option prefix is reserved for any options this plugin stores (none yet, but
 * kept so the contract matches the Python and future routes stay namespaced).
 * ==================================================================== */
define( 'PETFREEDOM_NS', 'petfreedom/v1' );
define( 'PETFREEDOM_OPT_PREFIX', 'pf_' );

/* ----------------------------------------------------------------------
 * DISCOVERY LINKS — shown on the admin "Get Started" page only.
 * PETFREEDOM_GITHUB is the public repo for the Pet Freedom skill (update it
 * if you fork). The skill itself is always distributed from GitHub,
 * regardless of WP.org listing.
 * -------------------------------------------------------------------- */
define( 'PETFREEDOM_GITHUB', 'https://github.com/blonderoofrat/pet-freedom' );
define( 'PETFREEDOM_HOME',   'https://blonderoofrat.com' );
/* One-click "try it live in your browser" — a WordPress Playground demo preloaded with the resource. */
define( 'PETFREEDOM_DEMO',   'https://playground.wordpress.net/?blueprint-url=https://raw.githubusercontent.com/blonderoofrat/pet-freedom/main/demo/playground/blueprint.json' );

add_action( 'rest_api_init', function () {

	// Single permission gate for every route below: site admins only.
	$admin = function () { return current_user_can( 'manage_options' ); };

	/* ------------------------------------------------------------------
	 * POST META — generic read/write.
	 *   GET  /meta?post_id=          -> all meta for the post
	 *   POST /meta {post_id, meta:{k:v}}  -> loop update_post_meta;
	 *        a null value deletes that key.
	 * This is what lets the skill write SEO meta (Rank Math `rank_math_*`,
	 * Yoast `_yoast_wpseo_*`, or core keys registered by the mu-plugin).
	 * ---------------------------------------------------------------- */
	register_rest_route( PETFREEDOM_NS, '/meta', array(
		array(
			'methods'             => WP_REST_Server::READABLE, // GET
			'permission_callback' => $admin,
			'args'                => array( 'post_id' => array( 'required' => true ) ),
			'callback'            => function ( WP_REST_Request $req ) {
				$id = intval( $req->get_param( 'post_id' ) );
				if ( ! $id || ! get_post( $id ) ) {
					return new WP_Error( 'petfreedom_no_post', 'No such post.', array( 'status' => 404 ) );
				}
				return array( 'post_id' => $id, 'meta' => get_post_meta( $id ) );
			},
		),
		array(
			'methods'             => WP_REST_Server::CREATABLE, // POST
			'permission_callback' => $admin,
			'callback'            => function ( WP_REST_Request $req ) {
				$id   = intval( $req->get_param( 'post_id' ) );
				$meta = $req->get_param( 'meta' );
				if ( ! $id || ! get_post( $id ) ) {
					return new WP_Error( 'petfreedom_no_post', 'No such post.', array( 'status' => 404 ) );
				}
				if ( ! is_array( $meta ) ) {
					return new WP_Error( 'petfreedom_bad_meta', 'meta must be an object of key:value.', array( 'status' => 400 ) );
				}
				$updated = array();
				foreach ( $meta as $k => $v ) {
					$k = sanitize_key( (string) $k );
					if ( $k === '' ) { continue; }
					if ( $v === null ) {
						delete_post_meta( $id, $k );
						$updated[ $k ] = null;
					} else {
						update_post_meta( $id, $k, $v );
						$updated[ $k ] = $v;
					}
				}
				return array( 'ok' => true, 'post_id' => $id, 'updated' => $updated );
			},
		),
	) );
} );

/* ======================================================================
 * ADMIN PAGE — "Get Started" (info only).
 * Gives the plugin standalone, user-facing value: it explains what Pet
 * Freedom is, what else you need (Claude Code + the free skill), shows
 * whether the REST route is active, and surfaces the two config
 * constants to keep in sync with config.json. It registers NO new routes,
 * collects NO data, and writes nothing — it only reads and renders.
 * ==================================================================== */
add_action( 'admin_menu', function () {
	add_menu_page(
		'Pet Freedom',                 // page <title>
		'Pet Freedom',                 // menu label
		'manage_options',              // capability
		'pet-freedom',                 // menu slug
		'pet_freedom_render_get_started',
		'dashicons-pets',
		71                             // position
	);
} );

if ( ! function_exists( 'pet_freedom_render_get_started' ) ) {
	/**
	 * Renders the read-only "Get Started" admin page. Info only — no forms,
	 * no writes, no data collection.
	 */
	function pet_freedom_render_get_started() {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_die( esc_html__( 'You do not have permission to view this page.', 'pet-freedom-companion' ) );
		}

		// "Is the REST route live?" — it is registered above on this install,
		// so if the plugin is active it exists. Build a sample URL so the admin
		// can confirm with their own credentials.
		$routes_active = true; // registered unconditionally when active
		$base          = esc_url( rest_url( PETFREEDOM_NS . '/meta' ) );
		$github        = esc_url( PETFREEDOM_GITHUB );
		$home          = esc_url( PETFREEDOM_HOME );
		$claude        = esc_url( 'https://claude.com/claude-code' );
		$docs          = esc_url( trailingslashit( PETFREEDOM_GITHUB ) . 'blob/main/README.md' );
		$demo          = esc_url( PETFREEDOM_DEMO );
		$live          = esc_url( trailingslashit( PETFREEDOM_HOME ) . 'roof-rat-laws/' );
		?>
		<div class="wrap">
			<h1><span class="dashicons dashicons-pets" style="font-size:1.2em;vertical-align:-4px;"></span> Pet Freedom</h1>

			<p style="font-size:14px;max-width:760px;">
				<strong>Map a species' legal status across the world — and publish it as an honest,
				source-cited resource.</strong> Pet Freedom researches and verifies whether an animal can be
				<em>kept, bred, sold, and transported</em> across countries, states, and territories, then
				publishes the result as a structured, SEO-ready WordPress resource. It is species-agnostic
				(you set the species in one config file) and privacy-preserving (your credentials and private
				notes never leave your machine; published pages render only public-safe fields).
			</p>

			<p style="max-width:760px;">
				<a class="button button-primary button-hero" href="<?php echo $demo; ?>" target="_blank" rel="noopener">&#9654;&nbsp; See it live in your browser — no install</a>
				<span class="description" style="display:block;margin-top:6px;">Boots a real WordPress in your browser (via WordPress Playground), preloaded with the worldwide roof-rat law resource as a working example. Takes a few seconds to build. <strong>Prefer the real thing?</strong> Browse the live, maintained resource this skill produces &mdash; <a href="<?php echo $live; ?>" target="_blank" rel="noopener"><em>Are Roof Rats Legal?</em>, 100+ jurisdictions</a>.</span>
			</p>

			<div class="notice notice-info inline" style="max-width:760px;padding:12px 16px;margin:18px 0;">
				<h2 style="margin-top:0;">What you also need</h2>
				<p style="margin-bottom:8px;">
					This plugin is the small WordPress companion. The actual research-and-publish work is done by
					<strong>Claude Code</strong> plus the free, open-source <strong>Pet Freedom skill</strong>:
				</p>
				<ul style="list-style:disc;margin-left:22px;">
					<li><a href="<?php echo $claude; ?>" target="_blank" rel="noopener">Claude Code</a> — Anthropic's CLI agent.</li>
					<li>The <strong>Pet Freedom skill</strong> + its config (<code>config.json</code>), distributed on
						<a href="<?php echo $github; ?>" target="_blank" rel="noopener">GitHub</a>.</li>
					<li>A WordPress user with publish rights + an Application Password (you likely already have this).</li>
				</ul>
				<p style="margin-bottom:0;">
					Read the setup docs: <a href="<?php echo $docs; ?>" target="_blank" rel="noopener">Pet Freedom README on GitHub</a>.
				</p>
			</div>

			<div class="notice notice-success inline" style="max-width:760px;padding:12px 16px;margin:18px 0;">
				<h2 style="margin-top:0;">Let Claude set it up for you</h2>
				<p style="margin:.2em 0 .6em;">
					New to this? Copy the prompt below and paste it into <strong>Claude Code</strong>. It will walk you
					through the whole setup &mdash; <code>config.json</code>, your Application Password, whether to use this
					plugin or the bundled SEO fallback, seeding, and publishing &mdash; with clear step-by-step help for
					anything you do by hand, plus troubleshooting if something goes wrong. (Click in the box and press
					Ctrl/Cmd&#8209;A to select all, then copy.)
				</p>
				<textarea readonly rows="9" style="width:100%;max-width:760px;box-sizing:border-box;font-family:Menlo,Consolas,monospace;font-size:12px;line-height:1.5;padding:10px;background:#fff;">I want to use the Pet Freedom skill to research and publish the legal status of [SPECIES] as a pet on my WordPress site, and I'd like you to walk me through the whole setup and handle as much as you can.

Please: (1) make sure I have the Pet Freedom skill from https://github.com/blonderoofrat/pet-freedom and read its README, SKILL.md, and docs/INSTALL.md; (2) walk me through filling in config.json and .env, including exactly how to create a WordPress Application Password; (3) tell me whether I need this companion plugin or the bundled mu-plugin SEO fallback, and guide me through it; (4) seed a few jurisdictions, run the research and verification, and publish the pages.

For any step I must do by hand (accounts, installing a plugin, purging cache), give me clear numbered instructions and wait for me to confirm each one before moving on. If anything errors or looks wrong, diagnose it with me. Once setup is done, take over the research-and-publish work.</textarea>
			</div>

			<h2>Status</h2>
			<table class="widefat striped" style="max-width:760px;">
				<tbody>
					<tr>
						<td style="width:240px;"><strong>REST route</strong></td>
						<td>
							<?php if ( $routes_active ) : ?>
								<span style="color:#1a7f37;">&#10003; Active</span> — <code>/meta</code> registered under
								<code>/wp-json/<?php echo esc_html( PETFREEDOM_NS ); ?>/</code> (admin-only).
							<?php else : ?>
								<span style="color:#b32d2e;">Not active</span>
							<?php endif; ?>
						</td>
					</tr>
					<tr>
						<td><strong>Confirm the route</strong></td>
						<td>
							<code><?php echo $base; ?></code>
							<p class="description" style="margin:4px 0 0;">
								Returns <code>401</code> unless you call it authenticated as an admin — that is correct
								and means the gate is working.
							</p>
						</td>
					</tr>
					<tr>
						<td><strong>Plugin version</strong></td>
						<td><code>1.2.0</code></td>
					</tr>
				</tbody>
			</table>

			<h2>Keep these in sync with <code>config.json</code></h2>
			<p style="max-width:760px;">
				The two constants below (top of <code>pet-freedom-companion.php</code>) must match the
				<code>plugin.namespace</code> and <code>plugin.option_prefix</code> values in your skill's
				<code>config.json</code>, or the tooling will call routes that do not exist.
			</p>
			<table class="widefat striped" style="max-width:760px;">
				<thead><tr><th>Constant</th><th>Current value</th><th>config.json key</th></tr></thead>
				<tbody>
					<tr>
						<td><code>PETFREEDOM_NS</code></td>
						<td><code><?php echo esc_html( PETFREEDOM_NS ); ?></code></td>
						<td><code>plugin.namespace</code></td>
					</tr>
					<tr>
						<td><code>PETFREEDOM_OPT_PREFIX</code></td>
						<td><code><?php echo esc_html( PETFREEDOM_OPT_PREFIX ); ?></code></td>
						<td><code>plugin.option_prefix</code></td>
					</tr>
				</tbody>
			</table>

			<h2>Links</h2>
			<p>
				<a class="button button-primary" href="<?php echo $github; ?>" target="_blank" rel="noopener">Pet Freedom on GitHub</a>
				<a class="button" href="<?php echo $demo; ?>" target="_blank" rel="noopener">&#9654; Try the live demo</a>
				<a class="button" href="<?php echo $live; ?>" target="_blank" rel="noopener">Live example: Roof Rat Laws</a>
				<a class="button" href="<?php echo $home; ?>" target="_blank" rel="noopener">Project home (blonderoofrat.com)</a>
			</p>

			<hr style="margin:24px 0;max-width:760px;">
			<p style="max-width:760px;color:#646970;">
				<strong>Research aid, not legal advice.</strong> Laws change and are interpreted by local officials.
				Always verify with the responsible authority and read the source yourself. If you publish information
				produced with this tool, you are responsible for its accuracy and for following your local laws.
			</p>
		</div>
		<?php
	}
}

<?php
/**
 * Plugin Name: Pet Freedom Companion
 * Plugin URI:  https://github.com/blonderoofrat/pet-freedom
 * Description: Companion for the free Pet Freedom skill for Claude Code: map a pet species' legal status across jurisdictions worldwide and publish it as a sourced WordPress resource. Adds a friendly admin "Get Started" page plus optional admin-only REST helpers (SEO post-meta read/write + self-update). Research aid, not legal advice.
 * Version:     1.1.0
 * Author:      Pet Freedom (blonderoofrat.com)
 * Author URI:  https://blonderoofrat.com
 * License:     GPLv2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Requires at least: 5.8
 * Requires PHP: 7.4
 *
 * LICENSE NOTE: This WordPress plugin is licensed GPLv2-or-later so it is
 * compatible with the WordPress.org plugin directory. The wider Pet Freedom
 * project (the Claude Code skill, its Python tooling, and docs) is licensed
 * MIT (code) / CC BY 4.0 (docs) — see the GitHub repository.
 *
 * This is the SMALL, generalized companion — NOT a big games/garden plugin.
 * It implements exactly three REST concerns: post-meta read/write, install
 * inspect, and plugin self-update — plus an info-only admin page. Everything
 * species-/site-specific lives in your skill's config.json; nothing here
 * references any domain, owner, or species.
 *
 * Install: place this file at
 *   wp-content/plugins/pet-freedom-companion/pet-freedom-companion.php
 * then activate "Pet Freedom Companion" on the wp-admin Plugins screen.
 * Later upgrades flow through the /plugin-update endpoint (see README.md).
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

/* Self-update guards. 256 KB is plenty for any source/asset this skill ships. */
const PETFREEDOM_MAX_BYTES = 262144; // 256 * 1024

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

	/* ------------------------------------------------------------------
	 * INSPECT — read-only list of active plugins + versions, so the deploy
	 * script can confirm the version header bumped after a self-update.
	 * ---------------------------------------------------------------- */
	register_rest_route( PETFREEDOM_NS, '/inspect', array(
		'methods'             => WP_REST_Server::READABLE,
		'permission_callback' => $admin,
		'callback'            => function () {
			if ( ! function_exists( 'get_plugins' ) ) {
				require_once ABSPATH . 'wp-admin/includes/plugin.php';
			}
			$plugins = array();
			foreach ( get_plugins() as $file => $d ) {
				if ( ! is_plugin_active( $file ) ) { continue; }
				$plugins[] = array(
					'name'    => $d['Name'],
					'version' => $d['Version'],
					'active'  => true,
				);
			}
			return array(
				'wp_version' => get_bloginfo( 'version' ),
				'plugins'    => $plugins,
			);
		},
	) );

	/* ------------------------------------------------------------------
	 * PLUGIN SELF-UPDATE — admin-authenticated REST write of a file inside
	 * this plugin's OWN directory, so upgrades can be pushed from the Python
	 * deploy tool without touching wp-admin. Heavily guarded:
	 *   - permission: manage_options (admin auth, e.g. Application Password)
	 *   - filename whitelist: ^[a-z0-9_-]+\.(php|md|txt|json|css|js)$
	 *   - basename() applied to defeat any path-traversal attempt
	 *   - 256 KB size cap
	 *   - .php files MUST start with <?php (never write a fataling loader)
	 *   - optional sha256: if supplied, bytes must match (hash_equals)
	 *   - write target is plugin_dir_path(__FILE__) only
	 *   - rotates .bak.1 .. .bak.5 so a bad push can be reverted via SFTP
	 *   - flushes the plugins cache so the new Version: shows immediately
	 * The new code takes effect on the NEXT request; this response still runs
	 * under the old (in-memory) code.
	 *
	 * RECOVERY: a broken push that still begins with <?php can fatal the site.
	 * ALWAYS `php -l` the file before deploying. If it fataled, restore the
	 * newest .bak (rename .bak.1 back over the live file) via SFTP/file manager.
	 * ---------------------------------------------------------------- */
	register_rest_route( PETFREEDOM_NS, '/plugin-update', array(
		'methods'             => WP_REST_Server::CREATABLE, // POST
		'permission_callback' => $admin,
		'args'                => array(
			'filename'    => array( 'required' => true ),
			'content_b64' => array( 'required' => true ),
			'sha256'      => array( 'required' => false ),
		),
		'callback'            => function ( WP_REST_Request $req ) {
			$fname = basename( (string) $req->get_param( 'filename' ) );
			if ( ! preg_match( '/^[a-z0-9_-]+\.(php|md|txt|json|css|js)$/i', $fname ) ) {
				return new WP_Error( 'petfreedom_bad_fname', 'Invalid filename (allowed: [a-z0-9_-]+ . php/md/txt/json/css/js).', array( 'status' => 400 ) );
			}
			$data = base64_decode( (string) $req->get_param( 'content_b64' ), true );
			if ( $data === false ) {
				return new WP_Error( 'petfreedom_bad_b64', 'content_b64 is not valid base64.', array( 'status' => 400 ) );
			}
			if ( strlen( $data ) > PETFREEDOM_MAX_BYTES ) {
				return new WP_Error( 'petfreedom_too_big', 'File exceeds 256 KB.', array( 'status' => 413 ) );
			}
			// .php must open with the PHP tag so we never write a broken loader.
			if ( strtolower( substr( $fname, -4 ) ) === '.php' && substr( $data, 0, 5 ) !== '<?php' ) {
				return new WP_Error( 'petfreedom_bad_php', 'PHP file must start with <?php', array( 'status' => 400 ) );
			}
			$expected_sha = (string) $req->get_param( 'sha256' );
			$actual_sha   = hash( 'sha256', $data );
			if ( $expected_sha !== '' && ! hash_equals( strtolower( $expected_sha ), $actual_sha ) ) {
				return new WP_Error( 'petfreedom_sha_mismatch',
					'sha256 mismatch: expected ' . $expected_sha . ' got ' . $actual_sha,
					array( 'status' => 400 ) );
			}
			$dir  = plugin_dir_path( __FILE__ );
			$path = $dir . $fname;
			// Rotate backups so the last 5 prior versions are recoverable via SFTP.
			if ( file_exists( $path ) ) {
				for ( $i = 5; $i > 1; $i-- ) {
					$src = $path . '.bak.' . ( $i - 1 );
					if ( file_exists( $src ) ) { @rename( $src, $path . '.bak.' . $i ); }
				}
				@copy( $path, $path . '.bak.1' );
			}
			if ( file_put_contents( $path, $data ) === false ) {
				return new WP_Error( 'petfreedom_write_failed', 'Could not write file (permissions?).', array( 'status' => 500 ) );
			}
			// Flush the cached plugins list so wp-admin shows the new Version:
			// header without a deactivate/reactivate cycle.
			if ( ! function_exists( 'wp_clean_plugins_cache' ) ) {
				require_once ABSPATH . 'wp-admin/includes/plugin.php';
			}
			wp_clean_plugins_cache( true );
			return array(
				'ok'       => true,
				'filename' => $fname,
				'bytes'    => strlen( $data ),
				'sha256'   => $actual_sha,
				'rel_path' => str_replace( WP_CONTENT_DIR, '', $path ),
				'note'     => 'plugin file replaced; new code takes effect on the NEXT request. Plugins-list cache flushed.',
			);
		},
	) );
} );

/* ======================================================================
 * ADMIN PAGE — "Get Started" (info only).
 * Gives the plugin standalone, user-facing value: it explains what Pet
 * Freedom is, what else you need (Claude Code + the free skill), shows
 * whether the REST routes are active, and surfaces the two config
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

		// "Are the REST routes live?" — they are registered above on this
		// install, so if the plugin is active they exist. Build a sample URL
		// so the admin can confirm with their own credentials.
		$routes_active = true; // registered unconditionally when active
		$base          = esc_url( rest_url( PETFREEDOM_NS . '/inspect' ) );
		$github        = esc_url( PETFREEDOM_GITHUB );
		$home          = esc_url( PETFREEDOM_HOME );
		$claude        = esc_url( 'https://claude.com/claude-code' );
		$docs          = esc_url( trailingslashit( PETFREEDOM_GITHUB ) . 'blob/main/README.md' );
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

			<h2>Status</h2>
			<table class="widefat striped" style="max-width:760px;">
				<tbody>
					<tr>
						<td style="width:240px;"><strong>REST routes</strong></td>
						<td>
							<?php if ( $routes_active ) : ?>
								<span style="color:#1a7f37;">&#10003; Active</span> — registered under
								<code>/wp-json/<?php echo esc_html( PETFREEDOM_NS ); ?>/</code>
								(<code>/meta</code>, <code>/inspect</code>, <code>/plugin-update</code>; all admin-only).
							<?php else : ?>
								<span style="color:#b32d2e;">Not active</span>
							<?php endif; ?>
						</td>
					</tr>
					<tr>
						<td><strong>Confirm a route</strong></td>
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
						<td><code>1.1.0</code></td>
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

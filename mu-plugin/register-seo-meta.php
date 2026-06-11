<?php
/**
 * Pet Freedom — SEO meta REST enabler (no-plugin fallback).
 *
 * Drop this file into wp-content/mu-plugins/ (create the folder if needed). It registers the SEO post-meta keys
 * with show_in_rest=true so the page builder can write them through CORE WordPress REST (/wp/v2/pages), WITHOUT
 * the optional companion plugin. Use this if config.json has "plugin":{"use":false}.
 *
 * Covers Rank Math and Yoast key names. Harmless if those SEO plugins aren't installed (the meta just sits unused).
 */
if (!defined('ABSPATH')) { exit; }

add_action('init', function () {
    $keys = array(
        // Rank Math
        'rank_math_title', 'rank_math_description', 'rank_math_focus_keyword', 'rank_math_canonical_url',
        // Yoast
        '_yoast_wpseo_title', '_yoast_wpseo_metadesc', '_yoast_wpseo_focuskw', '_yoast_wpseo_canonical',
    );
    foreach ($keys as $key) {
        register_post_meta('page', $key, array(
            'type'          => 'string',
            'single'        => true,
            'show_in_rest'  => true,
            'auth_callback' => function () { return current_user_can('edit_posts'); },
        ));
    }
});

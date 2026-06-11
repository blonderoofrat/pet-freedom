# -*- coding: utf-8 -*-
"""Pet Freedom — build a WordPress Playground "try it live" demo (WXR + blueprint.json), fully offline.

WHY: the biggest barrier to anyone adopting Pet Freedom is "that looks like a lot of setup (Claude Code +
a WordPress site + config)". A Playground demo removes it: one link boots a real WordPress in the visitor's
browser, preloaded with the resource, zero install. It makes the GitHub repo and the plugin listing far
more compelling, and it doubles as a screenshot source.

HOW: this reuses build.py's exact renderers, so the demo pages are identical to what the skill publishes to
a real site. It then rewrites internal navigation to ROOT-RELATIVE links so the whole hierarchy is clickable
inside the sandbox (no server, no network). Everything external — official sources, official agency contacts,
and your funnel/attribution CTAs — stays absolute. Output is a single shareable URL:

    https://playground.wordpress.net/?blueprint-url=<raw url to blueprint.json>

REUSABLE for ANY species: point --config at your config.json and --source at your jurisdiction JSONs; host
the two generated files next to a blueprint on any static host (GitHub raw works) and share the URL.

Dependency-free (stdlib only). Touches no network and needs no WordPress.
"""
import os
import sys
import glob
import json
import html
import argparse
import tempfile
import xml.dom.minidom as minidom

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SKILL_DIR)
sys.path.insert(0, SKILL_DIR)
import config  # noqa: E402  (imported before build so we can point CONFIG_PATH at the demo config)

# Internal links are rendered against this throwaway host, then stripped to "/..." (root-relative) so the
# demo is portable inside whatever origin Playground assigns. Must be a host that never appears in real data.
SENTINEL = "https://pf-demo.invalid"

# A worldwide, feature-complete showcase: every status, agency-confirmations, advocacy kits, and a US/Canada
# drill-down — chosen to look great fast. Ancestors are auto-included. Override with --include "id,id,...".
DEFAULT_SHOWCASE = ["us", "ca", "es", "ae", "nz", "fr", "nl", "se", "za", "de", "gb", "jp", "au", "sg", "ar",
                    "us-fl", "us-ma", "us-ca", "us-tx", "us-ak", "us-ny", "ca-bc", "ca-ab"]

RAW_BASE_DEFAULT = "https://raw.githubusercontent.com/blonderoofrat/pet-freedom/main/demo/playground/"


# ---------------------------------------------------------------- config plumbing
def _write_demo_config(base_path, funnel_base):
    """Load a base config, swap site.url for the SENTINEL, and make root-relative CTA links absolute against
    the real public site (funnel_base) so they survive the sentinel strip. Returns a temp config path."""
    data = json.load(open(base_path, encoding="utf-8"))
    data.setdefault("site", {})
    fb = (funnel_base or data["site"].get("url", "")).rstrip("/")
    cta = dict(data["site"].get("cta_links", {}) or {})
    for k, v in list(cta.items()):
        if v and v.startswith("/") and fb:
            cta[k] = fb + v
    data["site"]["url"] = SENTINEL
    data["site"]["cta_links"] = cta
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix="pfdemo_cfg_")
    os.close(fd)
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    return tmp


def _deabsolutize(htmlstr):
    """Strip the sentinel host so internal links become root-relative; external links are untouched."""
    return htmlstr.replace(SENTINEL + "/", "/").replace(SENTINEL, "")


# ---------------------------------------------------------------- WXR emit
def _cdata(s):
    """Wrap text in CDATA, escaping any literal ']]>' that would otherwise close the section early."""
    return "<![CDATA[%s]]>" % (s or "").replace("]]>", "]]]]><![CDATA[>")


WXR_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<rss version="2.0"\n'
    '  xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/"\n'
    '  xmlns:content="http://purl.org/rss/1.0/modules/content/"\n'
    '  xmlns:wfw="http://wellformedweb.org/CommentAPI/"\n'
    '  xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
    '  xmlns:wp="http://wordpress.org/export/1.2/">\n'
    "<channel>\n"
)


def _item(p, date):
    """One WXR <item> for a page dict: {id, parent, slug, title, content, path}."""
    return (
        "  <item>\n"
        "    <title>%s</title>\n"
        "    <link>%s%s</link>\n"
        "    <pubDate>%s</pubDate>\n"
        "    <dc:creator>%s</dc:creator>\n"
        '    <guid isPermaLink="false">pf-%s</guid>\n'
        "    <description></description>\n"
        "    <content:encoded>%s</content:encoded>\n"
        "    <excerpt:encoded>%s</excerpt:encoded>\n"
        "    <wp:post_id>%d</wp:post_id>\n"
        "    <wp:post_date>%s</wp:post_date>\n"
        "    <wp:post_date_gmt>%s</wp:post_date_gmt>\n"
        "    <wp:comment_status>%s</wp:comment_status>\n"
        "    <wp:ping_status>%s</wp:ping_status>\n"
        "    <wp:post_name>%s</wp:post_name>\n"
        "    <wp:status>%s</wp:status>\n"
        "    <wp:post_parent>%d</wp:post_parent>\n"
        "    <wp:menu_order>0</wp:menu_order>\n"
        "    <wp:post_type>%s</wp:post_type>\n"
        "    <wp:post_password></wp:post_password>\n"
        "    <wp:is_sticky>0</wp:is_sticky>\n"
        "  </item>\n"
        % (_cdata(html.unescape(p["title"])), SENTINEL, p["path"],
           date, _cdata("admin"), p["slug"], _cdata(p["content"]), _cdata(""),
           p["id"], _cdata(date), _cdata(date), _cdata("closed"), _cdata("closed"),
           _cdata(p["slug"]), _cdata("publish"), p["parent"], _cdata("page"))
    )


def _wxr(pages, title, desc, date):
    out = [WXR_HEADER]
    out.append("  <title>%s</title>\n  <link>%s</link>\n  <description>%s</description>\n"
               % (html.escape(title), SENTINEL, html.escape(desc)))
    out.append("  <pubDate>%s</pubDate>\n  <language>en-US</language>\n" % date)
    out.append("  <wp:wxr_version>1.2</wp:wxr_version>\n")
    out.append("  <wp:base_site_url>%s</wp:base_site_url>\n" % SENTINEL)
    out.append("  <wp:base_blog_url>%s</wp:base_blog_url>\n" % SENTINEL)
    out.append("  <wp:author><wp:author_id>1</wp:author_id><wp:author_login>%s</wp:author_login>"
               "<wp:author_email>%s</wp:author_email><wp:author_display_name>%s</wp:author_display_name>"
               "<wp:author_first_name>%s</wp:author_first_name><wp:author_last_name>%s</wp:author_last_name>"
               "</wp:author>\n"
               % (_cdata("admin"), _cdata("admin@example.com"), _cdata("admin"), _cdata(""), _cdata("")))
    for p in pages:
        out.append(_item(p, date))
    out.append("</channel>\n</rss>\n")
    return "".join(out)


# ---------------------------------------------------------------- page assembly
def _with_ancestors(ids, by_id):
    """Expand an id set to include every parent up to the root, so cross-links never dangle."""
    want = set()
    for jid in ids:
        cur = jid
        while cur and cur in by_id and cur not in want:
            want.add(cur)
            cur = by_id[cur]["jurisdiction"].get("parent")
    return want


def build_pages(build, juris, by_id, date):
    """Render the hub, About, finder, and one page per jurisdiction into WXR page dicts (parents first)."""
    pages = []
    HUB_ID, ABOUT_ID, FIND_ID = 2, 3, 4
    hub_path = build.cfg.hub_path
    pages.append(dict(id=HUB_ID, parent=0, slug=build.cfg.hub_slug, title=build.cfg.hub_title, path=hub_path,
                      content=_deabsolutize(build.with_footer(build.render(build.hub_blocks(juris, by_id))))))
    pages.append(dict(id=ABOUT_ID, parent=HUB_ID, slug="about", title="About This Resource & How We Research",
                      path=hub_path + "about/",
                      content=_deabsolutize(build.with_footer(build.render(build.about_blocks())))))
    pages.append(dict(id=FIND_ID, parent=HUB_ID, slug="find-your-local-law",
                      title="How to Find Your Local Law (Step by Step)", path=hub_path + "find-your-local-law/",
                      content=_deabsolutize(build.with_footer(build.render(build.selfhelp_blocks())))))
    next_id = 10
    idmap = {}
    for d in sorted(juris, key=lambda x: build.depth(x, by_id)):
        jid = d["jurisdiction"]["id"]
        pj = d["jurisdiction"].get("parent")
        parent = idmap.get(pj, HUB_ID) if (pj and pj in by_id) else HUB_ID
        pages.append(dict(id=next_id, parent=parent, slug=build.slug_for(d), title=build.title_for(d),
                          path=build.path_for(jid, by_id),
                          content=_deabsolutize(build.with_footer(build.render(build.jurisdiction_blocks(d, by_id))))))
        idmap[jid] = next_id
        next_id += 1
    return pages


# ---------------------------------------------------------------- blueprint emit
# Readability CSS for the demo — applied via the active theme's Custom CSS (printed in wp_head by core), so
# pages read well in Playground's default theme regardless of its block spacing. Keep it free of quotes/$.
DEMO_CSS = (
    ".entry-content,.wp-block-post-content{line-height:1.65;font-size:1.04rem;}"
    ".entry-content p,.wp-block-post-content p{margin:0 0 1.1em;}"
    ".entry-content h2,.wp-block-post-content h2{margin-top:1.9em;margin-bottom:.5em;line-height:1.25;}"
    ".entry-content h3,.wp-block-post-content h3{margin-top:1.2em;}"
    ".entry-content li,.wp-block-post-content li{margin:.4em 0;line-height:1.55;}"
    ".entry-content ul,.wp-block-post-content ul{margin-bottom:1.1em;}"
    "details summary{padding:.25em 0;}pre{line-height:1.5;}"
)


def blueprint(wxr_url, hub_path, blogname, tagline):
    setup_php = ("<?php require_once '/wordpress/wp-load.php'; "
                 "if (function_exists('wp_update_custom_css_post')) { wp_update_custom_css_post('%s'); } "
                 "flush_rewrite_rules(true);" % DEMO_CSS)
    return {
        "$schema": "https://playground.wordpress.net/blueprint-schema.json",
        "meta": {
            "title": blogname,
            "description": tagline,
            "author": "blonderoofrat",
            "categories": ["Demo"],
        },
        "landingPage": hub_path,
        "preferredVersions": {"php": "8.3", "wp": "latest"},
        "login": True,
        "steps": [
            {"step": "setSiteOptions", "options": {
                "blogname": blogname,
                "blogdescription": tagline,
                "permalink_structure": "/%postname%/",
            }},
            {"step": "importWxr", "file": {"resource": "url", "url": wxr_url}},
            {"step": "runPHP", "code": setup_php},
        ],
    }


# ---------------------------------------------------------------- driver
def generate(build, juris_all, by_id_all, include, out_dir, wxr_name, blueprint_name, wxr_url, date,
             blogname, tagline):
    if include:
        keep = _with_ancestors(include, by_id_all)
        juris = [d for d in juris_all if d["jurisdiction"]["id"] in keep]
    else:
        juris = juris_all
    by_id = {d["jurisdiction"]["id"]: d for d in juris}
    build._PATHS.clear()  # path cache is keyed by id; clear between curated/full runs
    pages = build_pages(build, juris, by_id, date)
    # The sentinel is used ONLY as the WXR's structural "old site URL" (base_blog_url / item links, which
    # the importer remaps). It must never survive in a visitor-facing page BODY — every internal link there
    # should already be root-relative.
    leaked = [p["slug"] for p in pages if SENTINEL in p["content"]]
    assert not leaked, "sentinel leaked into page body content: %s" % leaked
    wxr = _wxr(pages, blogname, tagline, date)
    minidom.parseString(wxr.encode("utf-8"))  # fail loudly if the XML is malformed
    bp = blueprint(wxr_url, build.cfg.hub_path, blogname, tagline)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, wxr_name), "w", encoding="utf-8") as fh:
        fh.write(wxr)
    with open(os.path.join(out_dir, blueprint_name), "w", encoding="utf-8") as fh:
        json.dump(bp, fh, indent=2, ensure_ascii=False)
    return len(pages)


def main():
    ap = argparse.ArgumentParser(description="Generate a WordPress Playground demo (WXR + blueprint) offline.")
    ap.add_argument("--config", default=os.path.join(ROOT, "demo", "playground", "demo.config.json"),
                    help="base config.json (species/site/CTAs). Default: the roof-rat demo config.")
    ap.add_argument("--source", default=os.path.join(ROOT, "demo", "roof-rat"),
                    help="dir of jurisdiction JSONs. Default: the bundled roof-rat demo dataset.")
    ap.add_argument("--out", default=os.path.join(ROOT, "demo", "playground"),
                    help="output dir for the WXR + blueprint files.")
    ap.add_argument("--funnel-base", default="",
                    help="absolute base URL for CTA/funnel links (default: the base config's site.url).")
    ap.add_argument("--raw-base", default=RAW_BASE_DEFAULT,
                    help="raw URL prefix where the generated files will be hosted (used inside the blueprint).")
    ap.add_argument("--include", default=",".join(DEFAULT_SHOWCASE),
                    help='comma-separated jurisdiction ids for the curated demo (ancestors auto-added). '
                         'Pass "all" to skip curation.')
    ap.add_argument("--full", action="store_true", help="ALSO emit a full (every-jurisdiction) demo pair.")
    ap.add_argument("--date", default="2026-06-11 00:00:00", help="fixed post date stamped into the WXR.")
    args = ap.parse_args()

    base_cfg = os.path.abspath(args.config)
    funnel_base = args.funnel_base or (json.load(open(base_cfg, encoding="utf-8")).get("site", {}) or {}).get("url", "")
    config.CONFIG_PATH = _write_demo_config(base_cfg, funnel_base)
    import build  # noqa: E402  (now binds build.cfg to the demo config)

    files = sorted(glob.glob(os.path.join(os.path.abspath(args.source), "*.json")))
    juris_all = [json.load(open(f, encoding="utf-8")) for f in files]
    by_id_all = {d["jurisdiction"]["id"]: d for d in juris_all}

    blogname = "Roof Rat Laws — a Pet Freedom live demo"
    tagline = ("Is it legal to keep a roof rat? A worldwide, source-cited demo built with the free "
               "Pet Freedom skill for Claude Code.")

    include = None if args.include.strip().lower() == "all" else \
        [x.strip() for x in args.include.split(",") if x.strip()]

    n = generate(build, juris_all, by_id_all, include, os.path.abspath(args.out),
                 "pet-freedom-demo.xml", "blueprint.json", args.raw_base + "pet-freedom-demo.xml",
                 args.date, blogname, tagline)
    print("curated demo : %3d pages -> %s" % (n, os.path.join(args.out, "blueprint.json")))
    play = "https://playground.wordpress.net/?blueprint-url=" + args.raw_base + "blueprint.json"
    print("              try-it-live: " + play)

    if args.full:
        nf = generate(build, juris_all, by_id_all, None, os.path.abspath(args.out),
                      "pet-freedom-full.xml", "blueprint-full.json", args.raw_base + "pet-freedom-full.xml",
                      args.date, blogname + " (full dataset)", tagline)
        print("full demo    : %3d pages -> %s" % (nf, os.path.join(args.out, "blueprint-full.json")))
        print("              try-it-live: https://playground.wordpress.net/?blueprint-url="
              + args.raw_base + "blueprint-full.json")

    os.unlink(config.CONFIG_PATH)


if __name__ == "__main__":
    main()

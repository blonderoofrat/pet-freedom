# -*- coding: utf-8 -*-
"""Pet Freedom — render and publish the legal-status section from data/jurisdictions/*.json.

Species/brand/site-agnostic port of the original project builder: every species name, site URL, slug,
SEO key, CTA, and attribution string comes from config.json (via config.Config). Adding a jurisdiction =
add a JSON file + rerun (no code change). Builds the hub, About/methodology, the self-help finder, and one
hierarchical page per jurisdiction. Idempotent (upserts by slug+parent, never cross-parent clobber; forces
status=publish, comments closed). Public pages render ONLY public-safe fields — never the private
contacts[]/research_log[]/notes. Preliminary (web-researched, unverified) jurisdictions get a clear banner.
See planning/legal/SCHEMA.md. Dependency-free (stdlib only)."""
import os, sys, glob, json, datetime, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, common

cfg = config.load()

# ---- dry-run / offline render state (set in main() from CLI flags) ----
# When DRY_RUN is True the builder touches NO network: upsert() renders each page body to
# pet-freedom/out/<slug-path>.html instead of calling the WordPress REST API or writing post meta.
DRY_RUN = False
SOURCE_DIR = None  # override for the jurisdiction-JSON source dir (else cfg.data_dir())
OUT_DIR = os.path.join(config.ROOT, "out")

DISCLAIMER_SHORT = ("This is a research aid, not legal advice; rules change and are interpreted by local "
                    "officials. Verify with the official source before acting.")

STATUS_COLORS = {"legal": "#2e7d32", "legal_with_permit": "#1565c0", "restricted": "#ef6c00",
                 "prohibited": "#c62828", "unregulated_unclear": "#616161", "unknown": "#9e9e9e"}
STATUS_LABELS = {"legal": "Legal", "legal_with_permit": "Legal with a permit", "restricted": "Restricted",
                 "prohibited": "Prohibited", "unregulated_unclear": "Unregulated / unclear",
                 "unknown": "Not yet researched"}

# Readable activity names. Custom activity keys (not in this map) fall back to a title-cased label.
ACT_NAMES = {"keep": "Keeping / owning", "breed": "Breeding",
             "sell_give": "Selling or giving away", "transport": "Transport &amp; import"}

# verified_by values that mean "compiled from the web but not yet agency-confirmed" -> preliminary banner.
PRELIM_VERIFIED_BY = {"web-research", "claude-websearch"}

ARTICLE = {"United States", "United Kingdom", "Netherlands", "District of Columbia"}  # take "the" in prose

# Geographic regions for the hub browse. Species-agnostic (it's just geography); keyed by ISO-3166 alpha-2.
# Anything unmapped falls into "Other regions" so nothing is ever dropped. Order = display order.
_REGION_ORDER = ["north-america", "latin-america", "europe", "mena", "africa", "asia", "oceania", "other"]
_REGION_NAME = {"north-america": "North America", "latin-america": "Latin America &amp; Caribbean",
                "europe": "Europe", "mena": "Middle East &amp; North Africa", "africa": "Africa",
                "asia": "Asia", "oceania": "Oceania", "other": "Other regions"}
_ISO_REGION = {}
for _codes, _reg in [
    ("US CA MX", "north-america"),
    ("AR BR CL CO PE UY EC BO PY VE CR PA DO GT CU NI HN SV", "latin-america"),
    ("AT BE CH CZ DE DK ES FI FR GB GR HU IE IT NL NO PL PT RO RU SE SK IS LU HR SI EE LV LT BG RS UA CY MT AL MD GE", "europe"),
    ("AE IL TR SA QA KW BH OM JO LB EG MA TN DZ IR IQ YE", "mena"),
    ("ZA NG KE GH ET TZ UG SN CI CM ZW ZM RW BW NA MU", "africa"),
    ("HK ID IN JP KR MY PH SG TH TW VN CN PK BD LK NP KH LA MM MN KZ", "asia"),
    ("AU NZ FJ PG", "oceania"),
]:
    for _c in _codes.split():
        _ISO_REGION[_c] = _reg

_PATHS = {}


# ---------- small species/text helpers ----------
def _species_common():
    return cfg.species_common


def _species_latin():
    return cfg.species_latin


def _i(s):
    """Italicize a Latin name (empty-safe)."""
    return ("<em>%s</em>" % s) if s else s


def act_name(key):
    return ACT_NAMES.get(key, key.replace("_", " ").capitalize())


# ---------- derivation ----------
def slug_for(d):
    return d["jurisdiction"].get("slug") or common.slugify(d["jurisdiction"]["name"])


def path_for(jid, by_id):
    if jid in _PATHS:
        return _PATHS[jid]
    d = by_id[jid]
    p = d["jurisdiction"].get("parent")
    base = path_for(p, by_id) if (p and p in by_id) else cfg.hub_path
    _PATHS[jid] = base + slug_for(d) + "/"
    return _PATHS[jid]


def _art(name):
    return "the " if name in ARTICLE else ""


def _place(d):
    return _art(d["jurisdiction"]["name"]) + d["jurisdiction"]["name"]


def title_for(d):
    return "Is it legal to keep a %s in %s? Keeping, Breeding &amp; Selling" % (_species_common(), _place(d))


def seo_title_for(d):
    # Shorter than the H1 so the SERP title (with the site-name suffix) stays under ~60 chars.
    return "Is it legal to keep a %s in %s?" % (_species_common(), _place(d))


def kw_for(d):
    return ("is it legal to keep a %s in %s" % (_species_common(), _place(d))).lower()


def desc_for(d):
    s = d.get("summary", "") or ""
    return (s[:150].rsplit(" ", 1)[0] + "…") if len(s) > 152 else s


def is_preliminary(d):
    return any(a.get("needs_verification") and a.get("verified_by") in PRELIM_VERIFIED_BY
               for a in d.get("activities", {}).values())


# ---------- block helpers (the original render mini-DSL) ----------
def render(blocks):
    out = []
    for kind, val in blocks:
        if kind == "h2":
            out.append('<!-- wp:heading -->\n<h2 class="wp-block-heading">%s</h2>\n<!-- /wp:heading -->' % val)
        elif kind == "h3":
            out.append('<!-- wp:heading {"level":3} -->\n<h3 class="wp-block-heading">%s</h3>\n<!-- /wp:heading -->' % val)
        elif kind == "p":
            out.append('<!-- wp:paragraph -->\n<p>%s</p>\n<!-- /wp:paragraph -->' % val)
        elif kind == "ul":
            items = "\n".join('<!-- wp:list-item -->\n<li>%s</li>\n<!-- /wp:list-item -->' % li for li in val)
            out.append('<!-- wp:list -->\n<ul class="wp-block-list">\n%s\n</ul>\n<!-- /wp:list -->' % items)
        elif kind == "raw":
            out.append(val)
    return "\n\n".join(out)


def html_block(inner):
    return "<!-- wp:html -->\n%s\n<!-- /wp:html -->" % inner


def callout(inner, bg="#fff8e1", border="#ffb300"):
    return html_block('<div style="background:%s;border-left:4px solid %s;padding:12px 16px;'
                      'border-radius:6px;margin:1em 0;">%s</div>' % (bg, border, inner))


def disclaimer_callout():
    return callout("<strong>Research aid, not legal advice.</strong> %s" % DISCLAIMER_SHORT)


def preliminary_callout():
    contact = cfg.cta_link("contact")
    tail = (' <a href="%s">Know the local rule? Tell us.</a>' % contact) if contact else ""
    return callout("<strong>Preliminary — independently researched, not yet agency-confirmed.</strong> "
                   "We compiled this from official sources but are still verifying it (and, where useful, "
                   "asking the agencies directly). Treat it as a starting point and confirm with the "
                   "official source." + tail,
                   bg="#fff3e0", border="#ef6c00")


def badge(status):
    color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
    label = STATUS_LABELS.get(status, STATUS_LABELS["unknown"])
    return ('<span style="display:inline-block;padding:2px 12px;border-radius:12px;font-weight:700;'
            'color:#fff;background:%s;font-size:.85em;white-space:nowrap;">%s</span>' % (color, label))


def src_links(ids, sources):
    by = {s["id"]: s for s in sources}
    return ", ".join('<a href="%s" rel="nofollow noopener" target="_blank">%s</a>' % (by[i]["url"], by[i]["authority"])
                     for i in (ids or []) if i in by) or "official sources listed below"


def activity_block(key, a, sources):
    inner = ('<h3 style="margin:.2em 0;">%s &nbsp; %s</h3>'
             '<p style="margin:.2em 0;color:#666;font-size:.85em;">Confidence: %s '
             '&middot; Last verified %s</p>'
             '<p style="margin:.4em 0;">%s</p>'
             '<p style="margin:.2em 0;font-size:.85em;color:#555;">Sources: %s</p>'
             % (act_name(key), badge(a["status"]), str(a.get("confidence", "")).capitalize(),
                a.get("verified_date", ""), a.get("why", ""), src_links(a.get("source_ids"), sources)))
    return html_block('<div style="border:1px solid #e0e0e0;border-radius:8px;padding:6px 16px;margin:.7em 0;">%s</div>' % inner)


def restriction_block(r, sources):
    parts = ["<strong>%s</strong>" % r.get("summary", "")]
    if r.get("steps"):
        parts.append("<ul style='margin:.4em 0 .4em 1.2em;'>" + "".join("<li>%s</li>" % s for s in r["steps"]) + "</ul>")
    meta = []
    if r.get("forms"):
        def _form_html(f):
            if isinstance(f, dict):
                nm = f.get("name", "")
                return '<a href="%s" rel="nofollow noopener" target="_blank">%s</a>' % (f["url"], nm) if f.get("url") else nm
            return f  # plain string form name (no URL)
        meta.append("Forms: " + ", ".join(_form_html(f) for f in r["forms"]))
    if r.get("where_to_file"):
        meta.append("Where: " + r["where_to_file"])
    if r.get("fees"):
        meta.append("Fees: " + r["fees"])
    if meta:
        parts.append('<p style="font-size:.85em;color:#555;margin:.3em 0;">' + " &middot; ".join(meta) + "</p>")
    if r.get("source_ids"):
        parts.append('<p style="font-size:.8em;color:#555;margin:.2em 0;">Source: ' + src_links(r["source_ids"], sources) + "</p>")
    return callout("".join(parts), bg="#fafafa", border="#9e9e9e")


def confirmations_callout(items):
    lis = "".join("<li>%s</li>" % x for x in items)
    return callout('<strong>Confirmed by the agencies.</strong><ul style="margin:.4em 0 0 1.2em;">%s</ul>' % lis,
                   bg="#e8f5e9", border="#2e7d32")


def interested_cta():
    care = cfg.cta_link("care")
    extra = cfg.cta_link("extra")
    contact = cfg.cta_link("contact")
    links = []
    if care:
        links.append('the <a href="%s">care &amp; husbandry guide</a>' % care)
    if extra:
        links.append('the <a href="%s">interactive guides</a>' % extra)
    if contact:
        links.append('<a href="%s">get in touch</a>' % contact)
    if not links:
        return ""
    if len(links) == 1:
        body = "Start with " + links[0] + "."
    else:
        body = "Start with " + ", ".join(links[:-1]) + ", or " + links[-1] + "."
    return callout("<strong>Thinking about keeping or breeding a %s?</strong> %s" % (_species_common(), body),
                   bg="#e3f2fd", border="#1565c0")


def restricted_cta(name):
    contact = cfg.cta_link("contact")
    latin = _i(_species_latin())
    tail = (' and <a href="%s">tell us what you learn</a> so we can help others' % contact) if contact else ""
    return callout("<strong>It appears you can't currently keep a %s as a pet in %s.</strong> "
                   "Please confirm with the official sources above before acting. If you'd like to see this "
                   "change, you can contact your representatives and the responsible agencies, ask them to "
                   "treat a domesticated %s line fairly%s."
                   % (_species_common(), name, latin, tail),
                   bg="#fff3e0", border="#ef6c00")


def verify_cta():
    contact = cfg.cta_link("contact")
    finder = cfg.site_url + cfg.hub_path + "find-your-local-law/"
    tail = (' and <a href="%s">send us what you find</a>' % contact) if contact else ""
    return callout("<strong>The rule here isn't settled yet.</strong> Use our "
                   '<a href="%s">step-by-step guide</a> to confirm with your agencies%s.'
                   % (finder, tail),
                   bg="#e3f2fd", border="#1565c0")


def vocab_table():
    rows = "".join('<tr><td style="padding:6px 10px;">%s</td><td style="padding:6px 10px;">%s</td></tr>' % (badge(k), desc)
                   for k, desc in [
                       ("legal", "Allowed, with no special permit."),
                       ("legal_with_permit", "Allowed, but a permit, license, or registration is required."),
                       ("restricted", "Allowed only under specific conditions or limits."),
                       ("prohibited", "Not allowed."),
                       ("unregulated_unclear", "No rule found, or the law is silent or ambiguous."),
                       ("unknown", "Not yet researched. Here is how you can help.")])
    return html_block('<table style="border-collapse:collapse;width:100%%;max-width:680px;">'
                      '<tbody>%s</tbody></table>' % rows)


# ---------- advocacy toolkit ----------
ADV_LANGNAME = {"en": "English", "es": "Español", "nl": "Nederlands", "fr": "Français",
                "de": "Deutsch", "it": "Italiano", "pt": "Português", "pl": "Polski",
                "ro": "Română", "el": "Ελληνικά", "ja": "日本語", "ko": "한국어",
                "ar": "العربية", "zh": "中文", "ru": "Русский", "tr": "Türkçe"}
ADV_BRANCH = {"agency": "executive / agency", "legislature": "legislature",
              "public_comment": "public comment", "court": "legal / judicial"}


def advocacy_block(d):
    """Advocacy toolkit, rendered when a jurisdiction has advocacy.kit.
    Bilingual (local legal language + English), with branch-correct touchpoints. Renders ONLY public-safe
    kit fields — never advocacy.notes / confidence_notes."""
    kit = (d.get("advocacy") or {}).get("kit") or {}
    if not kit:
        return ""
    name = d["jurisdiction"]["name"]
    P = []
    if kit.get("time_sensitive"):
        P.append('<div style="background:#fff3e0;border-left:4px solid #ef6c00;padding:8px 12px;'
                 'border-radius:6px;margin:.5em 0;"><strong>&#9203; Time-sensitive:</strong> %s</div>' % kit["time_sensitive"])
    if kit.get("problem"):
        P.append('<p style="margin:.5em 0;">%s</p>' % kit["problem"])
    if kit.get("ask"):
        P.append('<p style="margin:.5em 0;"><strong>The ask:</strong> %s</p>' % kit["ask"])
    if kit.get("branch_note"):
        P.append('<p style="margin:.5em 0;"><strong>Where the lever really is:</strong> %s</p>' % kit["branch_note"])
    tg = kit.get("targets") or []
    if tg:
        lis = []
        for t in tg:
            chan = ""
            if t.get("email"):
                chan = ' &mdash; <a href="mailto:%s">%s</a>' % (t["email"], t["email"])
            elif t.get("form_url"):
                chan = ' &mdash; <a href="%s" target="_blank" rel="noopener">official contact page</a>' % t["form_url"]
            b = ADV_BRANCH.get(t.get("type", ""), t.get("type", ""))
            lis.append('<li style="margin:.35em 0;"><strong>%s</strong> '
                       '<span style="font-size:.85em;color:#555;">(%s)</span>%s'
                       '<br><span style="color:#555;font-size:.92em;">%s</span></li>'
                       % (t.get("name", ""), b, chan, t.get("why", "")))
        P.append('<p style="margin:.6em 0 .2em;"><strong>Where to send it (more than one channel helps):</strong></p>'
                 '<ul style="margin:.2em 0 .4em 1.1em;">' + "".join(lis) + "</ul>")
    tmpl = kit.get("template") or {}
    if tmpl:
        P.append('<p style="margin:.6em 0 .2em;"><strong>A starting-point message</strong> &mdash; please put it in '
                 'your own words; a short personal note carries far more weight than an identical form letter:</p>')
        order = (["en"] if "en" in tmpl else []) + [k for k in tmpl if k != "en"]
        for lang in order:
            esc = tmpl[lang].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            P.append('<div style="margin:.35em 0;"><div style="font-size:.85em;color:#555;margin-bottom:2px;">%s</div>'
                     '<pre style="white-space:pre-wrap;background:#fff;border:1px solid #ddd;border-radius:6px;'
                     'padding:10px 12px;font-family:system-ui,-apple-system,sans-serif;font-size:.92em;margin:0;">%s</pre></div>'
                     % (ADV_LANGNAME.get(lang, lang), esc))
    contact = cfg.cta_link("contact")
    if contact:
        P.append('<p style="margin:.6em 0 0;font-size:.92em;">Did you take action, or get a response? '
                 '<a href="%s">Tell us</a> &mdash; it helps the next person, and we track what actually works.</p>' % contact)
    return ('<div style="background:#eef7ee;border:1px solid #bcdcbc;border-left:5px solid #2e7d32;border-radius:10px;'
            'padding:16px 18px;margin:1.5em 0;font-family:system-ui,-apple-system,sans-serif;line-height:1.55;">'
            '<strong style="color:#1b5e20;font-size:1.12em;">How to help in %s</strong>'
            % name + "".join(P) + "</div>")


# ---------- jurisdiction page ----------
def jurisdiction_blocks(d, by_id):
    j = d["jurisdiction"]
    name = j["name"]
    parent = j.get("parent")
    hub = cfg.site_url + cfg.hub_path
    if parent and parent in by_id:
        pn = by_id[parent]["jurisdiction"]["name"]
        blocks = [("p", '<a href="%s">%s</a> &rsaquo; <a href="%s%s">%s</a> &rsaquo; %s'
                        % (hub, cfg.hub_title, cfg.site_url, path_for(parent, by_id), pn, name))]
    else:
        blocks = [("p", '<a href="%s">%s</a> &rsaquo; %s' % (hub, cfg.hub_title, name))]
    blocks.append(("raw", disclaimer_callout()))
    if is_preliminary(d):
        blocks.append(("raw", preliminary_callout()))
    if parent and parent in by_id:
        pn2 = by_id[parent]["jurisdiction"]["name"]
        blocks.append(("raw", callout(
            "<strong>National law also applies.</strong> These are the %s-specific rules; "
            "%s&rsquo;s national rules (for example, breeder/dealer licensing and import/export) apply on "
            'top of them, and this page&rsquo;s answers inherit them only where %s is silent. See '
            '<a href="%s%s">%s</a>.'
            % (name, pn2, name, cfg.site_url, path_for(parent, by_id), pn2),
            bg="#eef2ff", border="#3949ab")))
    blocks.append(("p", "<strong>Summary.</strong> %s" % d.get("summary", "")))
    if d.get("agency_confirmations"):
        blocks.append(("raw", confirmations_callout(d["agency_confirmations"])))
    blocks.append(("h2", "Status by activity"))
    acts = d.get("activities", {})
    for key in cfg.activities:
        if key in acts:
            blocks.append(("raw", activity_block(key, acts[key], d.get("sources", []))))
    if d.get("restrictions"):
        blocks.append(("h2", "Restrictions &amp; responsibilities"))
        for r in d["restrictions"]:
            blocks.append(("raw", restriction_block(r, d.get("sources", []))))
    # status-aware call to action (keyed off the "keep" activity if present)
    ks = (acts.get("keep") or {}).get("status", "unknown")
    if ks in ("legal", "legal_with_permit"):
        cta = interested_cta()
    elif ks in ("prohibited", "restricted"):
        cta = restricted_cta(name)
    else:
        cta = verify_cta()
    if cta:
        blocks.append(("raw", cta))
    if (d.get("advocacy") or {}).get("kit"):
        blocks.append(("h2", "Help change this"))
        blocks.append(("raw", advocacy_block(d)))
    if d.get("sources"):
        blocks.append(("h2", "Official sources"))
        blocks.append(("ul", ['<a href="%s" rel="nofollow noopener" target="_blank">%s</a> &mdash; %s'
                              % (s["url"], s["title"], s["authority"]) for s in d["sources"]]))
    if j.get("local_terms"):
        blocks.append(("p", '<span style="font-size:.9em;color:#555;">Search terms: %s.</span>'
                            % ", ".join(j["local_terms"])))
    contact = cfg.cta_link("contact")
    tail = (' Spotted an error or an update? <a href="%s">Let us know</a>.' % contact) if contact else ""
    blocks.append(("p", "<em>Last reviewed %s. %s%s</em>" % (d.get("last_reviewed", ""), DISCLAIMER_SHORT, tail)))
    return blocks


# ---------- static pages ----------
def _region_of(d):
    return _ISO_REGION.get((d["jurisdiction"].get("iso") or "").upper(), "other")


def _child_label(kids):
    """Human label for a country's sub-jurisdictions, from their levels ('states & territories', 'provinces')."""
    levels = {k["jurisdiction"].get("level", "region") for k in kids}
    names = {"state": "states", "province": "provinces", "territory": "territories",
             "region": "regions", "county": "counties", "city": "cities"}
    parts = [names.get(l, l + "s") for l in ("state", "province", "territory", "region", "county", "city")
             if l in levels]
    return " &amp; ".join(parts) if parts else "areas"


# Hub accordion CSS (GOV.UK-style collapsible sections) + link affordance (NN/g: links colored AND underlined).
HUB_CSS = (
    '<style>'
    '.pf-hub details.pf-reg{border:1px solid #e3e6ea;border-radius:10px;background:#fafbfc;margin:.55em 0;}'
    '.pf-hub details.pf-reg>summary,.pf-hub details.pf-st>summary{list-style:none;cursor:pointer;}'
    '.pf-hub details.pf-reg>summary::-webkit-details-marker,.pf-hub details.pf-st>summary::-webkit-details-marker{display:none;}'
    '.pf-hub details.pf-reg>summary{display:flex;align-items:center;justify-content:space-between;gap:12px;'
    'padding:.7em 1em;font-weight:700;font-size:1.05em;color:#22303f;border-radius:10px;}'
    '.pf-hub details.pf-reg>summary:hover,.pf-hub details.pf-reg>summary:focus{background:#eef2f7;}'
    '.pf-hub .pf-cnt{color:#8a96a3;font-weight:500;font-size:.82em;}'
    '.pf-hub .pf-tog{display:inline-flex;align-items:center;gap:.4em;font-size:.8em;font-weight:600;color:#1565c0;white-space:nowrap;}'
    '.pf-hub .pf-caret{display:inline-block;transition:transform .15s ease;}'
    '.pf-hub details[open]>summary .pf-caret{transform:rotate(90deg);}'
    '.pf-hub details[open]>summary .pf-show{display:none;}'
    '.pf-hub details:not([open])>summary .pf-hide{display:none;}'
    '.pf-hub .pf-body{padding:.1em 1em .9em;}'
    '.pf-hub .pf-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:.5em 0;}'
    '.pf-hub a.pf-c{color:#1357b0;text-decoration:underline;font-weight:600;}'
    '.pf-hub a.pf-c:hover,.pf-hub a.pf-c:focus{color:#0c3e85;}'
    '.pf-hub details.pf-st{margin:.15em 0 .5em 1.1em;}'
    '.pf-hub details.pf-st>summary{color:#1565c0;font-size:.9em;font-weight:600;padding:.2em 0;}'
    '.pf-hub .pf-sub{margin:.5em 0 .3em;padding:.1em 0 .1em .9em;border-left:2px solid #e3e6ea;}'
    '.pf-hub .pf-jump{margin:.2em 0 1em;line-height:2.1;}'
    '.pf-hub .pf-chip{display:inline-block;background:#eef2ff;color:#26368c;border:1px solid #c5cae9;'
    'border-radius:14px;padding:4px 12px;margin:0 6px 0 0;font-size:.9em;text-decoration:none;font-weight:600;white-space:nowrap;}'
    '.pf-hub .pf-chip:hover,.pf-hub .pf-chip:focus{background:#e1e7ff;}'
    '.pf-hub .pf-allbtn{background:none;border:0;color:#1565c0;font-weight:600;cursor:pointer;'
    'text-decoration:underline;font-size:.88em;padding:0;margin-left:2px;}'
    '</style>'
)

# Opens a jump-chip's target region (regions are collapsed by default), toggles Expand/Collapse-all, and
# opens a region if the page is loaded with its #anchor. Progressive enhancement; the page works without JS.
HUB_JS = (
    '<script>(function(){'
    'function reg(id){var e=document.getElementById(id);'
    'if(e&&e.tagName.toLowerCase()==="details"){e.open=true;try{e.scrollIntoView({behavior:"smooth",block:"start"});}catch(_){}}}'
    'document.addEventListener("click",function(ev){'
    'var c=ev.target.closest?ev.target.closest("a.pf-chip"):null;'
    'if(c){ev.preventDefault();var id=c.getAttribute("href").slice(1);'
    'if(history.replaceState){history.replaceState(null,"","#"+id);}reg(id);return;}'
    'var b=ev.target.closest?ev.target.closest(".pf-allbtn"):null;'
    'if(b){ev.preventDefault();var op=b.getAttribute("data-op")!=="close";'
    'var ds=document.querySelectorAll(".pf-hub details.pf-reg");'
    'for(var i=0;i<ds.length;i++){ds[i].open=op;}'
    'b.setAttribute("data-op",op?"close":"open");b.textContent=op?"Collapse all":"Expand all";}'
    '});'
    'function fromHash(){if(location.hash.indexOf("#pf-reg-")===0){reg(location.hash.slice(1));}}'
    'window.addEventListener("hashchange",fromHash);fromHash();'
    '})();</script>'
)


def _country_row(c, juris, by_id):
    """One country: an underlined link + keep-status badge; sub-jurisdictions in their own collapsed expander."""
    nm = c["jurisdiction"]["name"]
    link = ('<a class="pf-c" href="%s%s" title="%s laws in %s%s">%s</a>'
            % (cfg.site_url, path_for(c["jurisdiction"]["id"], by_id), _species_common().capitalize(),
               _art(nm), nm, nm))
    row = ('<div class="pf-row">%s %s</div>'
           % (link, badge((c["activities"].get("keep") or {}).get("status", "unknown"))))
    kids = sorted([d for d in juris if d["jurisdiction"].get("parent") == c["jurisdiction"]["id"]],
                  key=lambda d: d["jurisdiction"]["name"])
    if kids:
        sub = "".join(
            '<div class="pf-row"><a class="pf-c" href="%s%s" title="%s laws in %s">%s</a> %s</div>'
            % (cfg.site_url, path_for(k["jurisdiction"]["id"], by_id), _species_common().capitalize(),
               k["jurisdiction"]["name"], k["jurisdiction"]["name"],
               badge((k["activities"].get("keep") or {}).get("status", "unknown"))) for k in kids)
        row += ('<details class="pf-st"><summary title="Click to show or hide">'
                '<span class="pf-tog"><span class="pf-show">Show</span><span class="pf-hide">Hide</span> '
                '%d %s <span class="pf-caret" aria-hidden="true">&#9656;</span></span>'
                '</summary><div class="pf-sub">%s</div></details>' % (len(kids), _child_label(kids), sub))
    return row


def hub_browse(juris, by_id):
    """Hub country index as a GOV.UK-style accordion: regions are COLLAPSED by default, each with a Show/Hide
    label + rotating caret and a tooltip; a jump-chip nav opens its target region; an Expand/Collapse-all
    control; countries are colored, underlined links with hover/title (NN/g). Replaces the old flat A–Z block."""
    countries = [d for d in juris if d["jurisdiction"].get("level") == "country"]
    by_region = {}
    for c in countries:
        by_region.setdefault(_region_of(c), []).append(c)
    present = [r for r in _REGION_ORDER if by_region.get(r)]

    jump = ""
    if len(present) > 1:
        chips = "".join('<a class="pf-chip" href="#pf-reg-%s" title="Open %s">%s (%d)</a>'
                        % (r, _REGION_NAME[r], _REGION_NAME[r], len(by_region[r])) for r in present)
        jump = ('<div class="pf-jump"><span style="font-size:.85em;color:#555;margin-right:2px;">'
                'Jump to a region:</span> %s '
                '<button type="button" class="pf-allbtn" data-op="open">Expand all</button></div>' % chips)

    sections = []
    for r in present:
        cs = sorted(by_region[r], key=lambda d: d["jurisdiction"]["name"])
        rows = "".join(_country_row(c, juris, by_id) for c in cs)
        sections.append(
            '<details class="pf-reg" id="pf-reg-%s"><summary title="Click to show or hide this region">'
            '<span>%s <span class="pf-cnt">&mdash; %d</span></span>'
            '<span class="pf-tog"><span class="pf-show">Show</span><span class="pf-hide">Hide</span> '
            '<span class="pf-caret" aria-hidden="true">&#9656;</span></span></summary>'
            '<div class="pf-body">%s</div></details>' % (r, _REGION_NAME[r], len(cs), rows))
    return html_block('<div class="pf-hub">%s%s%s%s</div>' % (HUB_CSS, jump, "".join(sections), HUB_JS))


def hub_blocks(juris, by_id):
    sc = _species_common()
    latin = _i(_species_latin())
    finder = cfg.site_url + cfg.hub_path + "find-your-local-law/"
    about = cfg.site_url + cfg.hub_path + "about/"
    contact = cfg.cta_link("contact")
    species_phrase = "%s (%s)" % (sc, latin) if latin else sc
    blocks = [
        ("p", "<strong>Before you can keep or breed a %s, you need to know one thing: is it legal where "
              "you live?</strong> This is a growing, plain-language guide to the official rules on keeping, "
              "breeding, selling, and transporting a domesticated %s, country by country and state by state, "
              "with links to the official sources so you can read them yourself." % (sc, species_phrase)),
        ("raw", disclaimer_callout()),
        ("h2", "Find your location"),
        ("p", "Open your region to see the countries in it, then pick your country (and your state or "
              "region). Each page breaks down the activities, with a confidence level and the official "
              "source for every answer. The badge shows whether <em>keeping</em> one as a pet is allowed."),
        ("raw", hub_browse(juris, by_id)),
    ]
    notseen = ('<strong>Don&rsquo;t see your area yet?</strong> We&rsquo;re adding jurisdictions over '
               'time. In the meantime, our <a href="%s">step-by-step guide to finding your local law</a> '
               "shows you exactly how to get the official answer for your area" % finder)
    if contact:
        notseen += ', and you can <a href="%s">send us what you find</a> so we can help the next person.' % contact
    else:
        notseen += "."
    blocks.append(("raw", callout(notseen, bg="#e3f2fd", border="#1565c0")))
    counterpart = cfg.counterpart
    if counterpart and counterpart.get("latin"):
        cp_phrase = _i(counterpart["latin"])
        cp_common = (counterpart.get("common") or [""])[0]
        if cp_common:
            cp_phrase += " (the %s)" % cp_common
        why = ("A %s can make a gentle, intelligent companion in a domesticated line, but it is a "
               "<strong>different species</strong> from %s, and the law sometimes treats them differently. "
               "Clear, honest legal information is the first step to keeping one responsibly, breeding the line "
               "forward, or advocating for fairer rules where it is restricted." % (sc, cp_phrase))
    else:
        why = ("A %s can make a gentle, intelligent companion in a domesticated line. Clear, honest legal "
               "information is the first step to keeping one responsibly, breeding the line forward, or "
               "advocating for fairer rules where it is restricted." % sc)
    blocks += [
        ("h2", "Why this matters"),
        ("p", why),
    ]
    ic = interested_cta()
    if ic:
        blocks.append(("raw", ic))
    blocks.append(("p", '<em>How we research these pages, and what our confidence levels and labels mean, is '
                        'explained in <a href="%s">About this resource</a>. %s</em>' % (about, DISCLAIMER_SHORT)))
    return blocks


def about_blocks():
    sc = _species_common()
    latin = _i(_species_latin())
    contact = cfg.cta_link("contact")
    species_phrase = "%s (%s)" % (sc, latin) if latin else sc
    blocks = [
        ("p", "This resource helps people find the official legal status of keeping, breeding, selling, and "
              "transporting a domesticated %s wherever they live, and what to do about it." % species_phrase),
        ("raw", disclaimer_callout()),
        ("h2", "What this is, and is not"),
        ("p", "It is a <strong>research aid</strong> built from official government sources. It is <strong>not "
              "legal advice</strong>, and we are not lawyers. Laws change, and local officials interpret them in "
              "ways we cannot control. Always read the official source yourself and, when it matters, confirm "
              "directly with the agency before you act."),
        ("h2", "How we research each jurisdiction"),
        ("ul", [
            "We start from <strong>official primary sources</strong>: statutes, regulations, and the responsible "
            "agencies (wildlife, agriculture, customs).",
            "We use structured deep research, then <strong>verify every claim against the official source</strong> and link it.",
            "Where the published rules are unclear, we say so, and where possible we confirm directly with the agency in writing.",
            "Every answer carries a <strong>confidence level</strong> and a <strong>last-verified date</strong>. "
            "Pages we have not yet agency-confirmed are marked <strong>preliminary</strong>.",
        ]),
        ("h2", "What the labels mean"),
        ("raw", vocab_table()),
    ]
    counterpart = cfg.counterpart
    if counterpart and counterpart.get("latin"):
        cp_latin = _i(counterpart["latin"])
        cp_common = (counterpart.get("common") or [""])[0]
        cp_phrase = cp_latin + ((" (the %s)" % cp_common) if cp_common else "")
        blocks += [
            ("h2", "Species, not domestication"),
            ("p", "An important nuance: most laws regulate a <em>species</em>, not whether your animals are tame. "
                  "A domesticated %s is still %s. So an exemption for &ldquo;domestic&rdquo; animals (which often "
                  "means only %s) may or may not cover a %s. We flag this wherever it matters, and it is often the "
                  "heart of the advocacy case for fairer rules."
                  % (sc, latin, cp_phrase, sc)),
        ]
    blocks.append(("h2", "Help us keep it accurate"))
    if contact:
        blocks.append(("p", 'Found something out of date, or know the rule for your area? Please '
                            '<a href="%s">tell us</a>, ideally with a link to the official source, and we will '
                            "verify and update. This resource gets better with every contribution." % contact))
    else:
        blocks.append(("p", "Found something out of date, or know the rule for your area? Send it our way with a "
                            "link to the official source, and we will verify and update. This resource gets better "
                            "with every contribution."))
    blocks.append(("p", "<em>%s</em>" % DISCLAIMER_SHORT))
    return blocks


def municipal_widget():
    """Generic city/county ordinance finder. Builds Google site: searches of the major municipal-code
    libraries for the local search terms. Not US-specific in wording (offers libraries as examples)."""
    sc = _species_common()
    contact = cfg.cta_link("contact")
    contact_html = (' Found your rule? <a href="%s">Tell us</a> and we will add your city.' % contact) if contact else ""
    return ('''<div style="max-width:680px;margin:1.4em 0;border:1px solid #ffcc66;background:#fff8e1;border-radius:10px;padding:16px 18px;font-family:system-ui,-apple-system,sans-serif;">
<strong style="color:#5d4037;font-size:1.08em;">Instant city / county ordinance finder</strong>
<p style="color:#5d4037;margin:.5em 0;">Local rules are the hardest layer to find. Type your city or region, and this builds ready-made searches of the major municipal-code libraries (Municode, American Legal Publishing, eCode360) plus a plain web search, for the words that matter. It opens an ordinary web search in a new tab; nothing is sent to us.</p>
<div style="display:flex;gap:8px;flex-wrap:wrap;margin:.6em 0;">
<input id="rrm-city" placeholder="City or county" style="flex:1;min-width:160px;padding:9px 11px;border:1px solid #ccc;border-radius:6px;font-size:1em;">
<input id="rrm-state" placeholder="State / region" style="flex:1;min-width:150px;padding:9px 11px;border:1px solid #ccc;border-radius:6px;font-size:1em;">
<button id="rrm-go" style="background:#ffb300;color:#3a2c20;border:0;border-radius:6px;padding:9px 18px;font-weight:700;cursor:pointer;font-size:1em;">Find</button>
</div>
<div id="rrm-out" style="margin-top:.4em;"></div>
<p style="color:#6d6d6d;font-size:.86em;margin:.7em 0 0;">Once you are in your code, search these terms: <em>rodent, exotic animal, wild animal, prohibited animal, number of pets / pet limit</em>.''' + contact_html + '''</p>
<script>(function(){
var b=document.getElementById('rrm-go');if(!b)return;
function esc(t){return (t||'').replace(/[<>]/g,'');}
function run(){
var c=esc(document.getElementById('rrm-city').value).trim();
var s=esc(document.getElementById('rrm-state').value).trim();
var out=document.getElementById('rrm-out');
if(!c){out.innerHTML='<span style="color:#c62828;">Please enter your city or county.</span>';return;}
var loc=c+(s?(' '+s):'');
var terms=' rodent OR exotic OR wildlife OR prohibited animal OR pet limit';
var hosts=[
['Municode library','site:library.municode.com '+loc+terms],
['American Legal Publishing','site:codelibrary.amlegal.com '+loc+terms],
['eCode360 (General Code)','site:ecode360.com '+loc+terms],
['Open web search',loc+' municipal code'+terms]
];
var h='<p style="margin:.4em 0 .2em;color:#5d4037;"><strong>Ready-made searches for '+loc+':</strong></p><ul style="margin:.2em 0 .2em 1.1em;padding:0;">';
for(var i=0;i<hosts.length;i++){h+='<li style="margin:.25em 0;"><a target="_blank" rel="noopener" href="https://www.google.com/search?q='+encodeURIComponent(hosts[i][1])+'">'+hosts[i][0]+'</a></li>';}
h+='</ul>';out.innerHTML=h;
}
b.addEventListener('click',run);
var st=document.getElementById('rrm-state');if(st){st.addEventListener('keydown',function(e){if(e.key==='Enter')run();});}
})();</script>
</div>''')


def selfhelp_blocks():
    sc = _species_common()
    latin = _i(_species_latin())
    contact = cfg.cta_link("contact")
    counterpart = cfg.counterpart
    # Step 1 prose adapts to whether a counterpart species is configured.
    if counterpart and counterpart.get("latin"):
        cp_latin = _i(counterpart["latin"])
        cp_common = (counterpart.get("common") or [""])[0]
        cp_clause = (" (also relevant: it is a <strong>different species</strong> from %s%s). Many rules that "
                     "exempt &ldquo;domestic&rdquo; animals mean only that other species, so do not assume."
                     % (cp_latin, (", the " + cp_common) if cp_common else ""))
    else:
        cp_clause = ""
    step1 = ("The pet %s is <strong>%s</strong>. When you contact an agency, use the scientific name and make "
             "clear the animals are <strong>captive-bred and kept as pets</strong>, not wild-caught.%s"
             % (sc, latin, cp_clause))
    blocks = [
        ("p", "<strong>Can&rsquo;t find your area in our guide yet?</strong> Here is exactly how to get the "
              "official answer for where you live, the same way we do it. It usually takes a few emails."),
        ("raw", disclaimer_callout()),
        ("h2", "Step 1: Know the exact animal"),
        ("p", step1),
        ("h2", "Step 2: Identify your jurisdiction(s)"),
        ("p", "Rules can stack at three levels: your <strong>country</strong>, your <strong>state or "
              "region</strong>, and your <strong>city or county</strong>. Check all three; a permissive country "
              "can still have a local ban, and vice versa."),
        ("h2", "Instant tool: check your city or county ordinance"),
        ("p", "The local layer is the hardest to research, because most city and county animal ordinances "
              "live in databases that are not indexed well by ordinary search. This finder builds targeted "
              "searches of the major municipal-code libraries for your area, scoped to the words that matter."),
        ("raw", municipal_widget()),
        ("h2", "Step 3: Ask the right agencies"),
        ("ul", [
            "<strong>Wildlife agency</strong>: non-native and captive-wildlife rules, a common place a "
            "non-traditional pet is regulated.",
            "<strong>Agriculture / animal-health department</strong>: sale, dealer licensing, and <strong>import health certificates</strong>.",
            "<strong>Customs / border or import authority</strong>: bringing animals across borders.",
            "<strong>Local animal control or city clerk</strong>: city and county ordinances.",
        ]),
        ("h2", "Step 4: Ask the questions, in writing"),
        ("p", "Email each agency and ask, specifically, about a %s kept as a pet:" % sc),
        ("ul", [
            "Is it legal to <strong>keep</strong> one as a pet? Any permit or registration?",
            "Is it legal to <strong>breed</strong> them? Any license?",
            "Is it legal to <strong>sell or give</strong> them to others? Any dealer license?",
            "What is required to <strong>transport or import</strong> them (health certificate, permit)?",
        ]),
        ("p", "Ask for the answer <strong>in writing</strong> and for the specific statute or rule, so you have "
              "a record and a citation. Write to the agency in the official language of your country."),
    ]
    if contact:
        blocks += [
            ("h2", "Step 5: Get it in writing, and share it"),
            ("p", 'Save the agency&rsquo;s reply. Then please <a href="%s">send it to us</a> with the source '
                  "links so we can verify it and add your area to the guide, helping the next person who asks." % contact),
        ]
    ic = interested_cta()
    if ic:
        blocks.append(("raw", ic))
    blocks.append(("p", "<em>%s</em>" % DISCLAIMER_SHORT))
    return blocks


# ---------- deploy ----------
def find_page(slug, parent_id):
    st, r = common.api_request(
        "GET", "/wp-json/wp/v2/pages?slug=%s&status=publish,draft&per_page=20&_fields=id,slug,parent" % slug)
    if st == 200 and isinstance(r, list) and r:
        for p in r:
            if int(p.get("parent", 0) or 0) == int(parent_id or 0):
                return p["id"]
        # NO cross-parent fallback (matching by slug alone once clobbered a root page in the original).
    return None


def _dry_write(slug, parent_id, title, content, path):
    """Offline branch of upsert: write the rendered page body to out/<slug-path>.html and report.

    Touches no network. Returns a synthetic (pid, link) so the page-ordering/hierarchy logic in main()
    keeps working unchanged. The synthetic pid is a stable string ('dry:<rel>') used only as a parent key.
    """
    rel = (path or ("/" + slug + "/")).strip("/")          # e.g. roof-rat-laws/us/texas
    fp = os.path.join(OUT_DIR, *(rel.split("/"))) + ".html"
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as fh:
        fh.write(content)
    link = (cfg.site_url + "/" + rel + "/") if cfg.site_url else ("/" + rel + "/")
    print("  would-publish  slug=%-22s parent=%-14s title=%s\n                 path=/%s/  ->  %s"
          % (slug, str(parent_id), title, rel, os.path.relpath(fp, config.ROOT)))
    return "dry:" + rel, link


def upsert(slug, parent_id, title, content, meta, path=None):
    if DRY_RUN:
        return _dry_write(slug, parent_id, title, content, path)
    pid = find_page(slug, parent_id)
    payload = {"title": title, "slug": slug, "status": "publish", "content": content,
               "parent": parent_id or 0, "comment_status": "closed", "ping_status": "closed"}
    if pid:
        st, r = common.api_request("POST", "/wp-json/wp/v2/pages/%d" % pid, payload); act = "updated"
    else:
        st, r = common.api_request("POST", "/wp-json/wp/v2/pages", payload); act = "created"
    if st not in (200, 201):
        raise SystemExit("FAILED %s: %s %s" % (slug, st, str(r)[:300]))
    pid = r.get("id"); link = r.get("link")
    if meta is not None:
        common.post_meta(cfg, pid, meta)
    print("  %-8s %-22s id=%s  %s" % (act, slug, pid, link))
    return pid, link


def meta_for(title, kw, desc, path):
    """Build the SEO meta dict for the configured plugin, or None to skip meta entirely."""
    plugin = cfg.seo_plugin
    canonical = cfg.site_url + path
    if plugin == "rank_math":
        return {"rank_math_title": "%s %%sep%% %%sitename%%" % title, "rank_math_description": desc,
                "rank_math_focus_keyword": kw, "rank_math_canonical_url": canonical}
    if plugin == "yoast":
        return {"_yoast_wpseo_title": "%s %%%%sep%%%% %%%%sitename%%%%" % title, "_yoast_wpseo_metadesc": desc,
                "_yoast_wpseo_focuskw": kw, "_yoast_wpseo_canonical": canonical}
    return None  # "none" -> skip meta entirely


def with_footer(content):
    """Append the optional attribution footer (HTML) if configured non-empty."""
    foot = cfg.attribution_footer()
    if not foot:
        return content
    return content + "\n\n" + html_block(
        '<p style="font-size:.85em;color:#888;text-align:center;margin-top:2em;">%s</p>' % foot)


def depth(d, by_id):
    n, p = 0, d["jurisdiction"].get("parent")
    while p and p in by_id:
        n += 1; p = by_id[p]["jurisdiction"].get("parent")
    return n


def main():
    src_dir = SOURCE_DIR or cfg.data_dir()
    files = sorted(glob.glob(os.path.join(src_dir, "*.json")))
    if not files:
        raise SystemExit("No jurisdiction JSONs in %s — add some and rerun." % src_dir)
    juris = [json.load(open(f, encoding="utf-8")) for f in files]
    by_id = {d["jurisdiction"]["id"]: d for d in juris}

    if DRY_RUN:
        print("DRY RUN — no network. Rendering pages to %s/" % os.path.relpath(OUT_DIR, config.ROOT))
    print("Building '%s' section on %s:" % (cfg.project_name, cfg.site_url))

    # Hub
    hub_meta = meta_for(cfg.hub_title, ("%s laws" % _species_common()).lower(),
                        "Official, plain-language guide to keeping, breeding, selling, and transporting a "
                        "pet %s by country and state, with sources." % _species_common(),
                        cfg.hub_path)
    hub_id, _ = upsert(cfg.hub_slug, 0, cfg.hub_title, with_footer(render(hub_blocks(juris, by_id))), hub_meta,
                       path=cfg.hub_path)

    # About / methodology
    upsert("about", hub_id, "About This Resource & How We Research",
           with_footer(render(about_blocks())),
           meta_for("How We Research These Laws", ("how %s laws are researched" % _species_common()).lower(),
                    "How this guide is researched: official sources, confidence levels, verified dates, and "
                    "what our labels mean. A research aid, not legal advice.",
                    cfg.hub_path + "about/"),
           path=cfg.hub_path + "about/")

    # Self-help finder
    upsert("find-your-local-law", hub_id, "How to Find Your Local Law (Step by Step)",
           with_footer(render(selfhelp_blocks())),
           meta_for("How to Find Your Local Law", ("find local %s laws" % _species_common()).lower(),
                    "A step-by-step guide to getting the official answer on keeping, breeding, selling, and "
                    "importing a pet %s for your country, state, and city." % _species_common(),
                    cfg.hub_path + "find-your-local-law/"),
           path=cfg.hub_path + "find-your-local-law/")

    # One page per jurisdiction, parents first so the hierarchy resolves.
    page_ids = {}
    for d in sorted(juris, key=lambda x: depth(x, by_id)):
        j = d["jurisdiction"]; jid = j["id"]; pj = j.get("parent")
        parent_page = hub_id if not (pj and pj in by_id) else page_ids[pj]
        pid, _ = upsert(slug_for(d), parent_page, title_for(d),
                        with_footer(render(jurisdiction_blocks(d, by_id))),
                        meta_for(seo_title_for(d), kw_for(d), desc_for(d), path_for(jid, by_id)),
                        path=path_for(jid, by_id))
        page_ids[jid] = pid

    total = 3 + len(page_ids)
    print("\nDONE. Hub id=%s. Jurisdiction pages: %d. Total pages: %d." % (hub_id, len(page_ids), total))
    print("Purge your host cache to show changes to visitors.")


def _parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Render and publish the Pet Freedom legal-status section. "
                    "By default it publishes to WordPress; --dry-run renders to disk with no network.")
    ap.add_argument("--source", metavar="DIR",
                    help="read jurisdiction JSONs from DIR instead of data/jurisdictions/.")
    ap.add_argument("--dry-run", action="store_true",
                    help="do NOT touch WordPress; write each rendered page body to out/<slug-path>.html "
                         "and print what would be published.")
    return ap.parse_args(argv)


if __name__ == "__main__":
    _args = _parse_args()
    if _args.source:
        SOURCE_DIR = os.path.abspath(_args.source)
    DRY_RUN = bool(_args.dry_run)
    main()

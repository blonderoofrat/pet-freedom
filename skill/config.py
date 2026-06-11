# -*- coding: utf-8 -*-
"""Pet Freedom — load + validate config.json (the single parameterization point) and resolve paths.

config.json is the ONLY place species/brand/host-specific values live. Copy config.example.json -> config.json.
This module is dependency-free (stdlib only) and is imported by every other skill script.
"""
import os
import json

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SKILL_DIR)                       # the pet-freedom/ repo root
CONFIG_PATH = os.path.join(ROOT, "config.json")
EXAMPLE_PATH = os.path.join(ROOT, "config.example.json")


def _strip_doc_keys(obj):
    """Drop documentation keys (anything starting with '_', e.g. _README / _note) recursively."""
    if isinstance(obj, dict):
        return {k: _strip_doc_keys(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, list):
        return [_strip_doc_keys(v) for v in obj]
    return obj


class Config:
    """Typed-ish accessors over config.json so the rest of the code never reaches into raw dicts."""

    def __init__(self, data):
        self.raw = data
        self.project = data.get("project", {})
        self.species = data.get("species", {})
        self.activities = data.get("activities") or ["keep", "breed", "sell_give", "transport"]
        self.site = data.get("site", {})
        self.seo = data.get("seo", {"plugin": "rank_math"})
        self.plugin = data.get("plugin", {"use": False})
        self.research = data.get("research", {})
        self.inquiries = data.get("inquiries", {"enabled": False})
        self.attribution = data.get("attribution", {})

    # ── project / site ──
    @property
    def project_name(self):
        return self.project.get("name", "Legal Status")

    @property
    def hub_slug(self):
        return (self.project.get("hub_slug", "laws") or "laws").strip("/")

    @property
    def hub_path(self):
        return "/%s/" % self.hub_slug

    @property
    def hub_title(self):
        return self.project.get("hub_title", self.project_name)

    @property
    def site_url(self):
        return (self.site.get("url", "") or "").rstrip("/")

    def cta_link(self, key):
        """Absolute URL for a configured CTA link ('care'|'extra'|'contact'); '' if unset."""
        rel = (self.site.get("cta_links", {}) or {}).get(key, "")
        if not rel:
            return ""
        return self.site_url + rel if rel.startswith("/") else rel

    # ── species ──
    @property
    def species_latin(self):
        return self.species.get("latin", "")

    @property
    def species_common(self):
        c = self.species.get("common") or []
        return c[0] if c else self.species_latin

    def species_common_all(self):
        return self.species.get("common") or []

    @property
    def counterpart(self):
        """The closely-related commonly-kept species dict, or None."""
        return self.species.get("counterpart") or None

    def local_terms_default(self):
        """Default local_terms for a new skeleton: latin + common names (+ counterpart latin for contrast searches)."""
        terms = [self.species_latin] + [c for c in self.species_common_all() if c]
        cp = self.counterpart
        if cp and cp.get("latin"):
            terms.append(cp["latin"])
        # de-dupe preserving order
        seen, out = set(), []
        for t in terms:
            if t and t not in seen:
                seen.add(t); out.append(t)
        return out

    # ── seo / plugin ──
    @property
    def seo_plugin(self):
        return (self.seo.get("plugin", "rank_math") or "rank_math").lower()  # rank_math | yoast | none

    @property
    def use_plugin(self):
        return bool(self.plugin.get("use", False))

    @property
    def plugin_namespace(self):
        return (self.plugin.get("namespace", "petfreedom/v1") or "petfreedom/v1").strip("/")

    @property
    def plugin_option_prefix(self):
        return self.plugin.get("option_prefix", "pf_")

    # ── research ──
    @property
    def gemini_available(self):
        return bool(self.research.get("gemini_available", False))

    @property
    def default_engine(self):
        return self.research.get("default_engine", "auto")  # auto | gemini | claude | manual

    # ── inquiries ──
    @property
    def inquiries_enabled(self):
        return bool(self.inquiries.get("enabled", False))

    @property
    def confirm_each(self):
        return bool(self.inquiries.get("confirm_each", True))

    # ── attribution ──
    def attribution_footer(self):
        """HTML for the opt-in footer, or '' if disabled."""
        if not self.attribution.get("footer_optin", False):
            return ""
        return self.attribution.get("footer_html", "")

    # ── paths (the adopter's working data lives under data/, gitignored) ──
    def data_dir(self):
        return os.path.join(ROOT, "data", "jurisdictions")

    def prompts_dir(self):
        return os.path.join(ROOT, "data", "prompts")

    def prompts_done_dir(self):
        return os.path.join(self.prompts_dir(), "done")

    def ensure_dirs(self):
        for d in (self.data_dir(), self.prompts_dir(), self.prompts_done_dir()):
            os.makedirs(d, exist_ok=True)
        return self


def load(path=None):
    """Load + minimally validate config.json. Raises SystemExit with a helpful message on problems."""
    p = path or CONFIG_PATH
    if not os.path.exists(p):
        raise SystemExit(
            "ERROR: no config.json at %s\n  -> copy config.example.json to config.json and edit it." % p
        )
    try:
        data = _strip_doc_keys(json.load(open(p, encoding="utf-8")))
    except json.JSONDecodeError as e:
        raise SystemExit("ERROR: config.json is not valid JSON: %s" % e)
    missing = []
    if not (data.get("species", {}) or {}).get("latin"):
        missing.append("species.latin")
    if not (data.get("site", {}) or {}).get("url"):
        missing.append("site.url")
    if not (data.get("project", {}) or {}).get("hub_slug"):
        missing.append("project.hub_slug")
    if missing:
        raise SystemExit("ERROR: config.json missing required value(s): " + ", ".join(missing))
    return Config(data)

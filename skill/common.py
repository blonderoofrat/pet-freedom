# -*- coding: utf-8 -*-
"""Pet Freedom — shared WordPress REST client + helpers (dependency-free).

Parses .env by hand and talks to WordPress over Basic auth (Application Passwords). Includes a transient-retry
client so a momentary 503/gateway blip never aborts a long publish run. No secrets are ever printed.
"""
import os
import sys
import json
import base64
import time
import urllib.request
import urllib.error

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SKILL_DIR)
ENV_PATH = os.path.join(ROOT, ".env")


def load_env(path=ENV_PATH):
    if not os.path.exists(path):
        raise SystemExit("ERROR: no .env at %s  (copy .env.example to .env and fill it in)" % path)
    env = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def get_config():
    """WordPress REST creds from .env: (url, user, app_password)."""
    env = load_env()
    url = (env.get("WP_URL") or "").rstrip("/")
    user = env.get("WP_USERNAME") or ""
    pw = env.get("WP_APP_PASSWORD") or ""
    missing = [k for k, v in (("WP_URL", url), ("WP_USERNAME", user), ("WP_APP_PASSWORD", pw)) if not v]
    if missing:
        raise SystemExit("ERROR: .env missing value(s) for: " + ", ".join(missing))
    pw = pw.replace(" ", "")  # WordPress shows app passwords in space-separated groups; spaces are cosmetic
    return url, user, pw


def _auth_header(user, pw):
    token = base64.b64encode(("%s:%s" % (user, pw)).encode("utf-8")).decode("ascii")
    return "Basic " + token


# Retry only genuinely transient conditions; a 4xx or plain 500 surfaces immediately.
_TRANSIENT_STATUS = {429, 502, 503, 504}


def _retry_after(headers):
    try:
        v = headers.get("Retry-After")
        if v and str(v).strip().isdigit():
            return min(float(str(v).strip()), 30.0)
    except Exception:
        pass
    return None


def api_request(method, path, data=None, timeout=45, retries=4, backoff=2.0):
    """Returns (status_code, parsed_body_or_text).

    Retries transient failures (HTTP 429/502/503/504 and network errors) with exponential backoff
    (honoring Retry-After). Raises only if a network failure persists after all retries.
    """
    url, user, pw = get_config()
    full = url + path
    body = None
    headers = {
        "Authorization": _auth_header(user, pw),
        "User-Agent": "pet-freedom/1.0",
        "Accept": "application/json",
    }
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    attempt = 0
    while True:
        req = urllib.request.Request(full, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8", errors="replace")
                try:
                    return r.status, json.loads(raw)
                except json.JSONDecodeError:
                    return r.status, raw
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            if e.code in _TRANSIENT_STATUS and attempt < retries:
                attempt += 1
                wait = _retry_after(e.headers) or min(backoff * (2 ** (attempt - 1)), 30.0)
                sys.stderr.write("  [retry %d/%d] %s %s -> %d; waiting %ds\n" % (attempt, retries, method, path, e.code, wait))
                time.sleep(wait)
                continue
            try:
                return e.code, json.loads(raw)
            except json.JSONDecodeError:
                return e.code, raw
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < retries:
                attempt += 1
                wait = min(backoff * (2 ** (attempt - 1)), 30.0)
                sys.stderr.write("  [retry %d/%d] %s %s -> network error (%s); waiting %ds\n" % (attempt, retries, method, path, e, wait))
                time.sleep(wait)
                continue
            raise


def slugify(title):
    import re
    s = (title or "").lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def naturalize(text, names=None):
    """Generic, OPT-IN name scrubber: replace any configured private name with a neutral placeholder.

    Pass a dict {private_name: replacement}; by default it is empty and this is a no-op. (In the original project
    this rewrote the owner's family names to first-person pronouns; in the shareable skill the name list is the
    adopter's own and ships empty, so no real person's name is hard-coded anywhere.)
    """
    import re
    names = names or {}
    if not names or not text:
        return text, []
    changes = []
    out = text
    for name, repl in names.items():
        pat = r"\b" + re.escape(name) + r"\b"
        if re.search(pat, out):
            changes.append((name, repl))
            out = re.sub(pat, repl, out)
    return out, changes


def post_meta(cfg, post_id, meta):
    """Write post meta either via the companion plugin's /<ns>/meta route or (no-plugin) core WP REST.

    With the mu-plugin SEO fallback registered, the rank_math_*/_yoast_* keys are REST-writable on the page itself.
    """
    if cfg.use_plugin:
        return api_request("POST", "/wp-json/%s/meta" % cfg.plugin_namespace, {"post_id": post_id, "meta": meta})
    # no-plugin path: write meta through core WP (requires the keys be registered show_in_rest — see mu-plugin)
    return api_request("POST", "/wp-json/wp/v2/pages/%d" % post_id, {"meta": meta})

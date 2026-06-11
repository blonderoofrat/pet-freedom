# -*- coding: utf-8 -*-
"""Pet Freedom — research-engine selector (pure advice; runs NO research itself).

Recommends, per jurisdiction, which Deep-Research engine to spend effort on, honoring
config.research:
  - gemini_available : bool — is Gemini Pro Deep Research an option for you?
  - default_engine   : auto | gemini | claude | manual

Decision logic (see recommend()):
  * default_engine != "auto"  -> that engine is the recommendation, EXCEPT a "gemini"
    default with gemini_available=False falls back to "claude" (with a note). We never
    block: if your chosen engine isn't available, you still get the best available one.
  * default_engine == "auto"  -> recommend GEMINI (when available) for the harder
    jurisdictions and CLAUDE otherwise. "Harder" heuristics:
        - non-English primary language (jurisdiction.language != "en"), OR
        - country-level scope (level == "country"), OR
        - any activity still unresolved (status in {unregulated_unclear, unknown})
          or low-confidence.
    If Gemini isn't available, always recommend CLAUDE ("best available fallback").

CLI:
  python skill/engine.py            # per-jurisdiction table for everything still PRELIMINARY
  python skill/engine.py --all      # include every jurisdiction (even verified)
  python skill/engine.py --json     # machine-readable

This tells the user WHERE to spend scarce Gemini effort; it does not fetch anything.
"""
import os
import sys
import glob
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

cfg = config.load()

# verified_by values that mark a still-preliminary (web-only) read — kept in sync with
# make_prompts.is_preliminary / build.is_preliminary.
_PRELIM_METHODS = {"web-research", "claude-websearch"}

# activity statuses that still need a real, possibly multilingual, deep dive.
_UNRESOLVED_STATUSES = {"unregulated_unclear", "unknown"}

ENGINE_GEMINI = "gemini"
ENGINE_CLAUDE = "claude"
ENGINE_MANUAL = "manual"


def is_preliminary(d):
    """True if any activity is a web-only read still flagged needs_verification."""
    return any(
        (a.get("verified_by") in _PRELIM_METHODS) and a.get("needs_verification")
        for a in (d.get("activities") or {}).values()
        if isinstance(a, dict)
    )


def _has_hard_activity(d):
    """True if any activity is unresolved (unknown/unclear) or low-confidence — i.e. worth Gemini."""
    for a in (d.get("activities") or {}).values():
        if not isinstance(a, dict):
            continue
        status = (a.get("status") or "").strip().lower()
        conf = (a.get("confidence") or "").strip().lower()
        if status in _UNRESOLVED_STATUSES or conf == "low":
            return True
    return False


def _is_complex(jur, d):
    """Higher-complexity heuristic for the 'auto' path."""
    language = (jur.get("language") or "").strip().lower()
    if language and language != "en":
        return True
    if (jur.get("level") or "").strip().lower() == "country":
        return True
    return _has_hard_activity(d)


def recommend(jur_dict):
    """Recommend an engine for one jurisdiction.

    Accepts either a full jurisdiction record (top-level "jurisdiction"/"activities" keys)
    or a bare jurisdiction descriptor dict. Returns {"engine": "...", "reason": "..."}.
    Never raises on shape; missing fields are treated conservatively (assume complexity).
    """
    jur_dict = jur_dict or {}
    # Tolerate both the full record and a bare descriptor.
    jur = jur_dict.get("jurisdiction") if isinstance(jur_dict.get("jurisdiction"), dict) else jur_dict
    full = jur_dict if isinstance(jur_dict.get("activities"), dict) else {}

    available = cfg.gemini_available
    default = (cfg.default_engine or "auto").strip().lower()

    # ── explicit (non-auto) default ──
    if default != "auto":
        if default == ENGINE_GEMINI and not available:
            return {
                "engine": ENGINE_CLAUDE,
                "reason": "default_engine=gemini but gemini_available=false — "
                          "falling back to Claude (best available).",
            }
        if default == ENGINE_GEMINI:
            return {"engine": ENGINE_GEMINI, "reason": "default_engine=gemini (forced)."}
        if default == ENGINE_CLAUDE:
            return {"engine": ENGINE_CLAUDE, "reason": "default_engine=claude (forced)."}
        if default == ENGINE_MANUAL:
            return {"engine": ENGINE_MANUAL, "reason": "default_engine=manual — you research it yourself."}
        # unknown value: behave like auto rather than erroring.

    # ── auto ──
    if not available:
        return {
            "engine": ENGINE_CLAUDE,
            "reason": "auto + Gemini unavailable — Claude deep-research/web-search is the best available fallback.",
        }

    if _is_complex(jur, full):
        bits = []
        lang = (jur.get("language") or "").strip().lower()
        if lang and lang != "en":
            bits.append("non-English primary language (%s)" % lang)
        if (jur.get("level") or "").strip().lower() == "country":
            bits.append("country-level scope")
        if _has_hard_activity(full):
            bits.append("unresolved/low-confidence activities")
        why = "; ".join(bits) or "higher complexity"
        return {"engine": ENGINE_GEMINI, "reason": "auto — %s — Gemini Deep Research recommended." % why}

    return {
        "engine": ENGINE_CLAUDE,
        "reason": "auto — English sub-national scope with no unresolved gaps — Claude web-search is sufficient.",
    }


def _load_records():
    """Yield (id, full_record) for every readable jurisdiction JSON in data_dir()."""
    out = []
    for p in sorted(glob.glob(os.path.join(cfg.data_dir(), "*.json"))):
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue  # skip unreadable/corrupt/empty files silently — read-only advice tool
        if not isinstance(data, dict):
            continue
        jur = data.get("jurisdiction") or {}
        jid = jur.get("id") or os.path.splitext(os.path.basename(p))[0]
        out.append((jid, data))
    return out


def build_rows(include_all=False):
    rows = []
    for jid, data in _load_records():
        prelim = is_preliminary(data)
        if not include_all and not prelim:
            continue
        jur = data.get("jurisdiction") or {}
        rec = recommend(data)
        rows.append({
            "id": jid,
            "name": jur.get("name", ""),
            "level": jur.get("level", ""),
            "language": jur.get("language", ""),
            "preliminary": prelim,
            "engine": rec["engine"],
            "reason": rec["reason"],
        })
    return rows


def _print_table(rows):
    if not rows:
        print("No matching jurisdictions found in %s" % cfg.data_dir())
        return
    id_w = max(2, max(len(r["id"]) for r in rows))
    name_w = max(4, min(28, max(len(r["name"]) for r in rows)))
    eng_w = max(6, max(len(r["engine"]) for r in rows))
    header = "%-*s  %-*s  %-*s  %s" % (id_w, "ID", name_w, "NAME", eng_w, "ENGINE", "REASON")
    print(header)
    print("-" * len(header))
    for r in rows:
        name = r["name"][:name_w]
        print("%-*s  %-*s  %-*s  %s" % (id_w, r["id"], name_w, name, eng_w, r["engine"], r["reason"]))


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Recommend the best Deep-Research engine per (preliminary) jurisdiction. Pure advice — runs no research."
    )
    p.add_argument("--all", action="store_true", help="include every jurisdiction, not just preliminary ones")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    args = p.parse_args(argv)

    rows = build_rows(include_all=args.all)
    n_gemini = sum(1 for r in rows if r["engine"] == ENGINE_GEMINI)
    n_claude = sum(1 for r in rows if r["engine"] == ENGINE_CLAUDE)
    n_manual = sum(1 for r in rows if r["engine"] == ENGINE_MANUAL)
    summary = (
        "Gemini available: %s; %d jurisdiction(s) recommended for Gemini, %d for Claude%s."
        % (
            "yes" if cfg.gemini_available else "no",
            n_gemini,
            n_claude,
            (", %d for manual" % n_manual) if n_manual else "",
        )
    )

    if args.json:
        print(json.dumps({
            "gemini_available": cfg.gemini_available,
            "default_engine": cfg.default_engine,
            "counts": {"gemini": n_gemini, "claude": n_claude, "manual": n_manual, "total": len(rows)},
            "summary": summary,
            "recommendations": rows,
        }, indent=2, ensure_ascii=False))
        return

    _print_table(rows)
    print()
    print(summary)


if __name__ == "__main__":
    main()

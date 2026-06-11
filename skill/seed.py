# -*- coding: utf-8 -*-
"""Pet Freedom — bulk jurisdiction seeder.

Writes skeleton jurisdiction JSON files (one per place) so the research/verify loop has something to fill in.
This is the missing-but-needed first step: turn a starter pack (pure public geography) into a directory of
`data/jurisdictions/<id>.json` skeletons, then let the agent research each one.

Two modes:
  Bulk from packs:
    python skill/seed.py --pack us-states world-major
  Add one jurisdiction:
    python skill/seed.py --add us-tx --level state --parent us --name "Texas" --slug texas --country US --language en

Nothing species- or brand-specific lives here: the species/local terms come from config.json via
`cfg.local_terms_default()`, and the starter packs are pure geography. Never clobbers verified data — a file is
considered GRADUATED (and skipped) once any activity has been verified by a real source (verified_by not in
{"", "web-research", "claude-websearch"}) with needs_verification false.
"""
import os
import sys
import json
import glob
import argparse
import datetime

# Make `import config` work no matter where this is invoked from.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import config  # noqa: E402

cfg = config.load()

ROOT = os.path.dirname(_HERE)
PACKS_DIR = os.path.join(ROOT, "starter-packs")

# verified_by values that mean "still just a seed/preliminary pass" — safe to overwrite.
PRELIMINARY_VERIFIERS = {"", "web-research", "claude-websearch"}


def today_iso():
    return datetime.date.today().isoformat()


def is_graduated(path):
    """True if the file holds real verified data we must never clobber.

    Graduated == at least one activity verified by a non-preliminary source (e.g. gemini-dr / owner / an agency)
    AND not still flagged needs_verification. A skeleton or a preliminary web-research pass is NOT graduated.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        # Unreadable/corrupt: treat as graduated so we don't silently overwrite something we can't parse.
        return True
    acts = data.get("activities") or {}
    if not isinstance(acts, dict):
        return False
    for rec in acts.values():
        if not isinstance(rec, dict):
            continue
        verifier = (rec.get("verified_by") or "").strip().lower()
        needs = rec.get("needs_verification", True)
        if verifier and verifier not in PRELIMINARY_VERIFIERS and not needs:
            return True
    return False


def _derive_iso(jid, level):
    """Best-effort ISO code from the id when the pack doesn't supply one.

    Country -> the id upper-cased (`gb` -> `GB`). Sub-national `cc-xx` -> `CC-XX` (`us-tx` -> `US-TX`).
    Anything else -> "" (let the researcher fill it in).
    """
    if level == "country":
        return jid.upper()
    if "-" in jid:
        cc, _, sub = jid.partition("-")
        if cc and sub:
            return "%s-%s" % (cc.upper(), sub.upper())
    return ""


def skeleton(entry):
    """Build a schema-shaped skeleton dict from a starter-pack entry.

    entry keys: id, level, parent, name; optional slug, country, iso, language.
    """
    jid = entry["id"]
    level = entry.get("level", "country")
    parent = entry.get("parent")
    if isinstance(parent, str) and parent.strip().lower() in ("none", "null", ""):
        parent = None
    name = entry.get("name", jid)
    slug = entry.get("slug") or jid
    country = entry.get("country", "")
    iso = entry.get("iso") or _derive_iso(jid, level)
    language = entry.get("language", "")
    today = today_iso()

    activities = {}
    for act in cfg.activities:
        activities[act] = {
            "status": "unknown",
            "confidence": "low",
            "why": "",
            "governing_law": "",
            "source_ids": [],
            "verified_date": "",
            "verified_by": "web-research",
            "needs_verification": True,
            "notes": "",
        }

    return {
        "jurisdiction": {
            "id": jid,
            "level": level,
            "name": name,
            "parent": parent,
            "country": country,
            "iso": iso,
            "language": language,
            "slug": slug,
            "local_terms": cfg.local_terms_default(),
        },
        "summary": "",
        "last_reviewed": today,
        "advocacy": {"flag": False, "notes": ""},
        "activities": activities,
        "restrictions": [],
        "sources": [],
        "contacts": [],
        "research_log": [
            {
                "date": today,
                "method": "seed",
                "note": "skeleton — needs preliminary research + verification",
            }
        ],
    }


def write_skeleton(entry):
    """Write one skeleton. Returns 'created' | 'refreshed' | 'skipped-graduated'.

    'created'  -> no file existed.
    'refreshed'-> a file existed but was still preliminary (skeleton/web-research), so it was re-seeded.
    'skipped-graduated' -> verified data present; left untouched.
    """
    jid = entry["id"]
    path = os.path.join(cfg.data_dir(), "%s.json" % jid)
    existed = os.path.exists(path)
    if existed and is_graduated(path):
        return "skipped-graduated"
    text = json.dumps(skeleton(entry), indent=2, ensure_ascii=False)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return "refreshed" if existed else "created"


def load_pack(name):
    """Load a starter pack list by name (without .json) from starter-packs/. Exits with a clear message if missing."""
    path = os.path.join(PACKS_DIR, "%s.json" % name)
    if not os.path.exists(path):
        avail = sorted(
            os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(PACKS_DIR, "*.json"))
        )
        raise SystemExit(
            "ERROR: no starter pack '%s' at %s\n  available: %s"
            % (name, path, ", ".join(avail) or "(none)")
        )
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError as e:
        raise SystemExit("ERROR: starter pack '%s' is not valid JSON: %s" % (name, e))
    if not isinstance(data, list):
        raise SystemExit("ERROR: starter pack '%s' must be a JSON list of entries." % name)
    return data


def run_packs(packs):
    cfg.ensure_dirs()
    created = refreshed = skipped_grad = 0
    seen_ids = set()
    for pack in packs:
        entries = load_pack(pack)
        print("== pack '%s' (%d entries) ==" % (pack, len(entries)))
        for entry in entries:
            if not isinstance(entry, dict) or "id" not in entry:
                print("  ! skipping malformed entry: %r" % (entry,))
                continue
            jid = entry["id"]
            if jid in seen_ids:
                continue  # same id across packs (e.g. 'us' parent) — handle once
            seen_ids.add(jid)
            result = write_skeleton(entry)
            if result == "created":
                created += 1
                print("  + %s (%s)" % (jid, entry.get("name", "")))
            elif result == "refreshed":
                refreshed += 1
                print("  ~ %s — refreshed (still preliminary)" % jid)
            else:  # skipped-graduated
                skipped_grad += 1
                print("  = %s — skipped (verified data present)" % jid)
    print(
        "\nDone: %d created, %d refreshed (preliminary), %d skipped (verified/graduated)."
        % (created, refreshed, skipped_grad)
    )
    return created


def run_add(args):
    cfg.ensure_dirs()
    entry = {
        "id": args.add,
        "level": args.level,
        "parent": args.parent,
        "name": args.name,
        "slug": args.slug or args.add,
        "country": args.country or "",
        "language": args.language or "",
    }
    result = write_skeleton(entry)
    path = os.path.join(cfg.data_dir(), "%s.json" % args.add)
    if result == "created":
        print("Created %s -> %s" % (args.add, path))
    elif result == "refreshed":
        print("Refreshed %s (was still preliminary) -> %s" % (args.add, path))
    else:  # skipped-graduated
        print("Skipped %s — verified data already present (not clobbered): %s" % (args.add, path))


def build_parser():
    p = argparse.ArgumentParser(
        description="Bulk-seed jurisdiction skeletons from starter packs (or add one)."
    )
    p.add_argument(
        "--pack",
        nargs="+",
        metavar="PACK",
        help="one or more starter-pack names (files in starter-packs/, without .json), e.g. us-states world-major",
    )
    p.add_argument("--add", metavar="ID", help="add a single jurisdiction by id (URL slug), e.g. us-tx")
    p.add_argument("--level", help="level for --add: country|state|province|territory|municipality")
    p.add_argument("--parent", help="parent id for --add, or 'none' for a top-level country")
    p.add_argument("--name", help="display name for --add, e.g. \"Texas\"")
    p.add_argument("--slug", help="URL slug for --add (defaults to the id)")
    p.add_argument("--country", help="ISO2 country code for --add, e.g. US")
    p.add_argument("--language", help="primary language code for --add, e.g. en")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.add:
        if not args.level or not args.name:
            raise SystemExit("ERROR: --add requires --level and --name (--parent defaults to none).")
        if args.parent is None:
            args.parent = "none"
        run_add(args)
    elif args.pack:
        run_packs(args.pack)
    else:
        build_parser().print_help()
        raise SystemExit("\nERROR: nothing to do — pass --pack <names...> or --add <id> ...")


if __name__ == "__main__":
    main()

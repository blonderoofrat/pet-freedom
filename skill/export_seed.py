# -*- coding: utf-8 -*-
"""Pet Freedom — export a SCRUBBED, public, shareable seed dataset from working jurisdiction JSONs.

The working files under data/jurisdictions/ are an investigative record: they carry an internal
`research_log` (our process notes, named officials, who we emailed and when), per-activity/contact `notes`
(process commentary), and `advocacy.notes` (internal strategy). NONE of that is meant to ship. This tool
reads a directory of working jurisdiction JSONs and writes a PUBLIC copy of each with the private fields
removed, so the result is safe to commit as a demo/seed dataset that others can fork.

Two things are PRIVACY-CRITICAL:
  1. Structural scrub — drop the private fields outright (research_log, *.notes, advocacy.notes).
  2. Name backstop — re-serialize each finished output and assert NONE of the scrub-names survive anywhere.
     If a name leaks (e.g. embedded in a `summary` or `why`), the file is SKIPPED with a loud warning and a
     human must fix the source wording. We never emit a file that still contains a scrub-name.

This tool does NOT mutate the source files. It only reads them and writes scrubbed copies to --target.

CLI examples:
    python skill/export_seed.py --source ../planning/legal/jurisdictions --target demo/roof-rat
    python skill/export_seed.py --target demo/roof-rat                       # source defaults to cfg.data_dir()
    python skill/export_seed.py --source data/jurisdictions --target demo/roof-rat --scrub-names "Jane Doe,Acme Co"

Dependency-free (stdlib only). Can run with or without a loaded config.json: --source defaults to the
adopter's working data dir from config when present, but a config is not required if --source is given.
"""
import os
import sys
import json
import glob
import re
import argparse

# Make `import config` work no matter where this is invoked from.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import config  # noqa: E402

# Backstop name list — names to REDACT from any output. EMPTY by default so no real person's name ships in
# this public code; pass YOUR private names with --scrub-names "Full Name,First,Partner" (case-insensitive,
# whole-word; longer names first so a full name is removed before a bare first name). Any output file in which
# a scrub-name still survives is SKIPPED, never written.
DEFAULT_SCRUB_NAMES = []

# ── Per-activity fields kept in the public copy (everything else on an activity is dropped). ──
ACTIVITY_PUBLIC_FIELDS = (
    "status",
    "confidence",
    "why",
    "governing_law",
    "source_ids",
    "verified_date",
    "needs_verification",
)
# `verified_by` is kept but mapped: "owner" -> "maintainer" (don't expose that the owner is the verifier).
# `notes` on an activity is process commentary -> DROPPED.

# ── Per-contact fields kept (official channel info only; `notes` is process commentary -> DROPPED). ──
CONTACT_PUBLIC_FIELDS = (
    "agency",
    "role",
    "email",
    "form_url",
    "phone",
    "primary",
    "inquiry_language",
)


def _public_activity(rec):
    """Return a scrubbed copy of one ActivityRecord: public fields only, verified_by 'owner'->'maintainer'."""
    if not isinstance(rec, dict):
        return rec
    out = {k: rec[k] for k in ACTIVITY_PUBLIC_FIELDS if k in rec}
    vb = rec.get("verified_by")
    if vb is not None:
        out["verified_by"] = "maintainer" if str(vb).strip().lower() == "owner" else vb
    return out


def _public_restriction(rec):
    """Return a scrubbed copy of one RestrictionRecord: same shape minus any `notes` field."""
    if not isinstance(rec, dict):
        return rec
    return {k: v for k, v in rec.items() if k != "notes"}


def _public_contact(rec):
    """Return a scrubbed copy of one contact: official channel fields only, dropping `notes` (process)."""
    if not isinstance(rec, dict):
        return rec
    return {k: rec[k] for k in CONTACT_PUBLIC_FIELDS if k in rec}


def _public_jurisdiction(block):
    """Copy the jurisdiction block as-is, but drop any jurisdiction-level `notes`."""
    if not isinstance(block, dict):
        return block
    return {k: v for k, v in block.items() if k != "notes"}


def _public_advocacy(block):
    """Keep advocacy.flag + advocacy.kit (full public kit); DROP advocacy.notes (internal strategy)."""
    if not isinstance(block, dict):
        return block
    out = {}
    if "flag" in block:
        out["flag"] = block["flag"]
    if "kit" in block:
        out["kit"] = block["kit"]
    return out


def scrub_object(data):
    """Build a public copy of a working jurisdiction object.

    KEEP: jurisdiction (minus notes), summary, last_reviewed, agency_confirmations[], activities (public
    fields only; verified_by owner->maintainer; activity notes dropped), restrictions[] (notes dropped),
    sources[], advocacy.flag + advocacy.kit, inquiry_focus, contacts[] (official channel fields only).
    DROP entirely: research_log, advocacy.notes, any jurisdiction/top-level `notes`.

    Only the name scrub touches wording; field text (summary/why/inquiry_focus) is left intact structurally.
    """
    if not isinstance(data, dict):
        return data
    out = {}

    if "jurisdiction" in data:
        out["jurisdiction"] = _public_jurisdiction(data["jurisdiction"])
    if "summary" in data:
        out["summary"] = data["summary"]
    if "last_reviewed" in data:
        out["last_reviewed"] = data["last_reviewed"]
    if "agency_confirmations" in data:
        out["agency_confirmations"] = data["agency_confirmations"]

    if "advocacy" in data:
        out["advocacy"] = _public_advocacy(data["advocacy"])

    acts = data.get("activities")
    if isinstance(acts, dict):
        out["activities"] = {k: _public_activity(v) for k, v in acts.items()}
    elif "activities" in data:
        out["activities"] = acts  # preserve unexpected shape rather than silently drop

    if isinstance(data.get("restrictions"), list):
        out["restrictions"] = [_public_restriction(r) for r in data["restrictions"]]

    if "inquiry_focus" in data:
        out["inquiry_focus"] = data["inquiry_focus"]

    if isinstance(data.get("sources"), list):
        out["sources"] = data["sources"]

    if isinstance(data.get("contacts"), list):
        out["contacts"] = [_public_contact(c) for c in data["contacts"]]

    # DROP entirely (never copied): research_log, advocacy.notes, top-level notes.
    return out


def _name_patterns(names):
    """Compile case-insensitive whole-word patterns for the scrub-names, longest first.

    Whole-word here means not flanked by another word character, so 'Dale' won't fire inside 'Dales' but
    will fire as a standalone token. Longest-first so multi-word names are removed before their substrings.
    """
    cleaned = [n.strip() for n in names if n and n.strip()]
    cleaned.sort(key=len, reverse=True)
    return [(n, re.compile(r"(?<!\w)" + re.escape(n) + r"(?!\w)", re.IGNORECASE)) for n in cleaned]


def scrub_names_in_text(text, patterns):
    """Remove every scrub-name occurrence from a string; collapse the doubled spaces that leaves."""
    if not text:
        return text
    out = text
    for _name, pat in patterns:
        out = pat.sub("", out)
    # Collapse runs of spaces/tabs created by deletion, and tidy a stray " ," / " ." left behind.
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    return out


def scrub_names_in_obj(obj, patterns):
    """Recursively apply the name scrub to every string value (and dict key) in a JSON-like object."""
    if isinstance(obj, dict):
        return {scrub_names_in_text(k, patterns): scrub_names_in_obj(v, patterns) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_names_in_obj(v, patterns) for v in obj]
    if isinstance(obj, str):
        return scrub_names_in_text(obj, patterns)
    return obj


def find_surviving_names(obj, patterns, path="$"):
    """Return a list of (json_path, scrub_name) for any scrub-name still present anywhere in obj.

    Used as the privacy backstop: if this is non-empty, the file is NOT emitted.
    """
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            for name, pat in patterns:
                if isinstance(k, str) and pat.search(k):
                    hits.append(("%s.<key:%s>" % (path, k), name))
            hits.extend(find_surviving_names(v, patterns, "%s.%s" % (path, k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(find_surviving_names(v, patterns, "%s[%d]" % (path, i)))
    elif isinstance(obj, str):
        for name, pat in patterns:
            if pat.search(obj):
                hits.append((path, name))
    return hits


def export_file(src_path, target_dir, patterns):
    """Scrub one source file and write its public copy. Returns (status, detail).

    status: 'exported' | 'skipped'.
    detail: for 'skipped', a human-readable reason; for 'exported', the output path.
    """
    fname = os.path.basename(src_path)
    try:
        with open(src_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        return "skipped", "unreadable/invalid JSON: %s" % e

    public = scrub_object(data)
    public = scrub_names_in_obj(public, patterns)

    # Privacy backstop: re-serialize and assert no scrub-name survives ANYWHERE.
    survivors = find_surviving_names(public, patterns)
    if survivors:
        where = "; ".join("%s contains \"%s\"" % (loc, name) for loc, name in survivors[:6])
        if len(survivors) > 6:
            where += " (+%d more)" % (len(survivors) - 6)
        return "skipped", "SCRUB-NAME SURVIVED -> %s" % where

    out_path = os.path.join(target_dir, fname)
    text = json.dumps(public, indent=2, ensure_ascii=False)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return "exported", out_path


def resolve_source(arg_source):
    """--source if given; else cfg.data_dir() from a loaded config; else a clear error."""
    if arg_source:
        return os.path.abspath(arg_source)
    try:
        cfg = config.load()
    except SystemExit as e:
        raise SystemExit(
            "ERROR: no --source given and config.json could not be loaded to default it.\n  %s" % e
        )
    return cfg.data_dir()


def build_parser():
    p = argparse.ArgumentParser(
        description="Export a SCRUBBED, public seed dataset from working jurisdiction JSONs."
    )
    p.add_argument(
        "--source",
        metavar="DIR",
        help="directory of working <id>.json files (default: config.json data_dir, if a config exists)",
    )
    p.add_argument(
        "--target",
        metavar="DIR",
        required=True,
        help="directory to write scrubbed public copies into (REQUIRED; created if missing)",
    )
    p.add_argument(
        "--scrub-names",
        metavar="NAMES",
        help="comma-separated names to redact anywhere in output (defaults to a built-in backstop list)",
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    source = resolve_source(args.source)
    target = os.path.abspath(args.target)

    if not os.path.isdir(source):
        raise SystemExit("ERROR: source is not a directory: %s" % source)
    if os.path.abspath(source) == target:
        raise SystemExit("ERROR: --target must differ from --source (refusing to overwrite working data).")

    if args.scrub_names:
        names = [n for n in args.scrub_names.split(",") if n.strip()]
    else:
        names = list(DEFAULT_SCRUB_NAMES)
    patterns = _name_patterns(names)

    src_files = sorted(glob.glob(os.path.join(source, "*.json")))
    if not src_files:
        raise SystemExit("ERROR: no *.json files found in source: %s" % source)

    os.makedirs(target, exist_ok=True)

    print("Exporting scrubbed seed dataset")
    print("  source: %s" % source)
    print("  target: %s" % target)
    print("  scrub-names: %s" % ", ".join(names))
    print("  files found: %d\n" % len(src_files))

    exported = 0
    skipped = []
    for src in src_files:
        status, detail = export_file(src, target, patterns)
        fname = os.path.basename(src)
        if status == "exported":
            exported += 1
            print("  + %s" % fname)
        else:
            skipped.append((fname, detail))
            # Loud, hard-to-miss warning for anything skipped — especially a surviving scrub-name.
            print("  !!! SKIPPED %s -> %s" % (fname, detail))

    print("\nDone: %d exported, %d skipped." % (exported, len(skipped)))
    if skipped:
        print("Skipped files (fix the source, then re-run):")
        for fname, detail in skipped:
            print("  - %s: %s" % (fname, detail))
    print("\nREVIEW the target dir before committing — confirm no private process notes or names remain.")
    return 0 if not skipped else 1


if __name__ == "__main__":
    sys.exit(main())

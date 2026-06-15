# -*- coding: utf-8 -*-
"""Pet Freedom — "audit for certainty" (READ-ONLY; never writes anything).

Scans data/jurisdictions/*.json and reports where our answers are still soft, so the skill
knows where to push for certainty — and, crucially, whether a clarifying inquiry to a real
agency is even possible (is there a usable contact?).

Per jurisdiction it flags an activity as a GAP when any of:
  - needs_verification == true, OR
  - status in {"unknown", "unregulated_unclear"}, OR
  - confidence == "low".

It also checks whether the jurisdiction has:
  - any sources[]  (can we cite an answer at all?), and
  - a usable contacts[] entry — an email or a form_url — (can we even ASK to close the gap?).

Each jurisdiction is classified:
  - VERIFIED        : no gaps.
  - PRELIMINARY     : has gaps AND a usable agency contact -> researchable / askable.
  - OPEN-NO-CONTACT : has gaps but NO usable contact -> can't send a clarifying inquiry yet.

The recommendation line is the signal the skill uses to SUGGEST sending inquiries:
  "N jurisdictions have clarification-worthy gaps with a usable agency contact —
   consider enabling inquiries (config.inquiries.enabled) to close them."

CLI:
  python skill/audit.py            # human-readable summary table + counts + recommendation
  python skill/audit.py --json     # machine-readable

Read-only: opens files, never modifies them.
"""
import os
import sys
import glob
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

cfg = config.load()

# Statuses that count as an unresolved answer.
_GAP_STATUSES = {"unknown", "unregulated_unclear"}

VERIFIED = "VERIFIED"
PRELIMINARY = "PRELIMINARY"
OPEN_NO_CONTACT = "OPEN-NO-CONTACT"


def _is_gap(activity):
    """True if this activity record still needs work."""
    if not isinstance(activity, dict):
        return True  # malformed -> treat as a gap to be safe
    if activity.get("needs_verification"):
        return True
    if (activity.get("status") or "").strip().lower() in _GAP_STATUSES:
        return True
    if (activity.get("confidence") or "").strip().lower() == "low":
        return True
    return False


def _has_usable_contact(data):
    """True if any contacts[] entry has an email or form_url (a channel to ask)."""
    for c in (data.get("contacts") or []):
        if not isinstance(c, dict):
            continue
        if (c.get("email") or "").strip() or (c.get("form_url") or "").strip():
            return True
    return False


def _has_sources(data):
    return bool(data.get("sources"))


_EMDASH = "—"


def _emdash_fields(data):
    """Public-rendered prose fields that contain an em-dash. In our OWN prose this is a VOICE violation
    (smooth it to commas/periods/parentheses); it is fine ONLY inside a quoted official source, which the
    audit cannot tell apart, so this is a soft 'review these' flag, not a hard failure."""
    hits = []
    if _EMDASH in (data.get("summary") or ""):
        hits.append("summary")
    for name, a in (data.get("activities") or {}).items():
        if isinstance(a, dict) and _EMDASH in (a.get("why") or ""):
            hits.append("activities.%s.why" % name)
    for i, r in enumerate(data.get("restrictions") or []):
        if isinstance(r, dict) and _EMDASH in (r.get("summary") or ""):
            hits.append("restrictions[%d].summary" % i)
    for i, c in enumerate(data.get("agency_confirmations") or []):
        if isinstance(c, str) and _EMDASH in c:
            hits.append("agency_confirmations[%d]" % i)
    return hits


def audit_record(data):
    """Audit one jurisdiction record -> dict of findings."""
    activities = data.get("activities") or {}
    gap_acts = []
    for name, a in activities.items():
        if _is_gap(a):
            rec = a if isinstance(a, dict) else {}
            gap_acts.append({
                "activity": name,
                "status": rec.get("status", ""),
                "confidence": rec.get("confidence", ""),
                "needs_verification": bool(rec.get("needs_verification")),
            })

    has_contact = _has_usable_contact(data)
    has_sources = _has_sources(data)
    voice_em_dash = _emdash_fields(data)

    if not gap_acts:
        klass = VERIFIED
    elif has_contact:
        klass = PRELIMINARY
    else:
        klass = OPEN_NO_CONTACT

    return {
        "classification": klass,
        "gap_count": len(gap_acts),
        "gaps": gap_acts,
        "has_contact": has_contact,
        "has_sources": has_sources,
        "voice_em_dash": voice_em_dash,
    }


def _load_records():
    """Yield (id, name, full_record) for every readable jurisdiction JSON in data_dir()."""
    out = []
    for p in sorted(glob.glob(os.path.join(cfg.data_dir(), "*.json"))):
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue  # skip unreadable/corrupt/empty — read-only audit
        if not isinstance(data, dict):
            continue
        jur = data.get("jurisdiction") or {}
        jid = jur.get("id") or os.path.splitext(os.path.basename(p))[0]
        out.append((jid, jur.get("name", ""), data))
    return out


def build_report():
    rows = []
    for jid, name, data in _load_records():
        finding = audit_record(data)
        finding["id"] = jid
        finding["name"] = name
        rows.append(finding)
    return rows


def _counts(rows):
    return {
        VERIFIED: sum(1 for r in rows if r["classification"] == VERIFIED),
        PRELIMINARY: sum(1 for r in rows if r["classification"] == PRELIMINARY),
        OPEN_NO_CONTACT: sum(1 for r in rows if r["classification"] == OPEN_NO_CONTACT),
    }


def _recommendation_line(rows):
    n = sum(1 for r in rows if r["classification"] == PRELIMINARY)
    no_contact = sum(1 for r in rows if r["classification"] == OPEN_NO_CONTACT)
    if n:
        line = (
            "%d jurisdiction(s) have clarification-worthy gaps with a usable agency contact — "
            "consider enabling inquiries (config.inquiries.enabled) to close them." % n
        )
    else:
        line = "No jurisdiction has a clarification-worthy gap with a usable agency contact."
    if no_contact:
        line += (
            "  (%d more have gaps but NO usable contact — find an agency email/form first.)" % no_contact
        )
    if cfg.inquiries_enabled and n:
        line += "  [inquiries already enabled]"
    return line


def _print_table(rows):
    if not rows:
        print("No jurisdiction files found in %s" % cfg.data_dir())
        return
    id_w = max(2, max(len(r["id"]) for r in rows))
    name_w = max(4, min(26, max(len(r["name"]) for r in rows)))
    cls_w = len(OPEN_NO_CONTACT)
    header = "%-*s  %-*s  %-*s  %4s  %3s  %4s" % (
        id_w, "ID", name_w, "NAME", cls_w, "CLASS", "GAPS", "SRC", "CONT")
    print(header)
    print("-" * len(header))
    for r in sorted(rows, key=lambda x: (x["classification"], x["id"])):
        print("%-*s  %-*s  %-*s  %4d  %3s  %4s" % (
            id_w, r["id"],
            name_w, r["name"][:name_w],
            cls_w, r["classification"],
            r["gap_count"],
            "yes" if r["has_sources"] else "no",
            "yes" if r["has_contact"] else "no",
        ))


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Audit jurisdiction data for certainty gaps (read-only). Reports where to push for verification."
    )
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    args = p.parse_args(argv)

    rows = build_report()
    counts = _counts(rows)
    rec = _recommendation_line(rows)

    if args.json:
        print(json.dumps({
            "total": len(rows),
            "counts": counts,
            "recommendation": rec,
            "inquiries_enabled": cfg.inquiries_enabled,
            "jurisdictions": rows,
        }, indent=2, ensure_ascii=False))
        return

    _print_table(rows)
    print()
    print("Totals: %d verified, %d preliminary (researchable), %d open / no contact  (of %d total)."
          % (counts[VERIFIED], counts[PRELIMINARY], counts[OPEN_NO_CONTACT], len(rows)))
    print(rec)
    vrows = [r for r in rows if r.get("voice_em_dash")]
    if vrows:
        print("Voice: %d jurisdiction(s) have em-dashes in public prose (smooth to commas/periods unless "
              "inside a quoted source): %s" % (len(vrows), ", ".join(r["id"] for r in vrows)))


if __name__ == "__main__":
    main()

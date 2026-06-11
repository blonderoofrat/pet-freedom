# -*- coding: utf-8 -*-
"""Pet Freedom — auto-generate a Deep-Research prompt for every PRELIMINARY jurisdiction
that doesn't already have one.

For each preliminary jurisdiction JSON in data/jurisdictions/, this fills the shared
templates/prompt.template.md with the jurisdiction descriptor + the configured species
(and optional counterpart) + the configured activity list, then appends a
"What we already found (PRELIMINARY -- VERIFY and CORRECT)" section built from our current
summary, per-activity statuses/reasoning, open questions, local terms, agency contact, and
sources. That gives the research engine our working answer to confirm or overturn.

- Idempotent: skips any jurisdiction that already has a prompt in data/prompts/ or
  data/prompts/done/ (so hand-tuned + verified ones are never clobbered).
- A jurisdiction is "preliminary" if any activity has verified_by in
  {"web-research","claude-websearch"} AND needs_verification truthy. Verified jurisdictions
  (gemini-dr / claude-deep-research / owner / agency) are skipped.

Nothing species- or brand-specific is hard-coded here: species, counterpart, and activities
all come from config.json via skill/config.py. The template carries placeholders only.

Run:  python skill/make_prompts.py
"""
import os
import sys
import glob
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import config  # noqa: E402

cfg = config.load()

TEMPLATE = os.path.join(config.ROOT, "templates", "prompt.template.md")

# verified_by values that mark a still-preliminary (web-only) read
_PRELIM_METHODS = {"web-research", "claude-websearch"}

# human descriptor for {{JURISDICTION}} based on level/parent
ARTICLE_STATE = "the U.S. state of {n}"
ARTICLE_TERR = "the U.S. territory of {n}"


def descriptor(j):
    """Human phrase for {{JURISDICTION}} based on level/parent."""
    n = j.get("name", "")
    lvl = j.get("level", "")
    parent = j.get("parent")
    if lvl == "state" and parent == "us":
        return ARTICLE_STATE.format(n=n)
    if lvl == "territory" and parent == "us":
        return ARTICLE_TERR.format(n=n)
    if lvl == "province" and parent == "ca":
        return "the Canadian province of %s" % n
    return n  # country (or anything else: use the bare name


def is_preliminary(d):
    return any(
        (a.get("verified_by") in _PRELIM_METHODS) and a.get("needs_verification")
        for a in (d.get("activities") or {}).values()
    )


def existing_prompt_ids():
    have = set()
    for base in (cfg.prompts_dir(), cfg.prompts_done_dir()):
        for p in glob.glob(os.path.join(base, "*.md")):
            have.add(os.path.splitext(os.path.basename(p))[0])
    return have


def counterpart_block():
    """The 'different species from the commonly-kept counterpart' nuance, or '' if none configured."""
    cp = cfg.counterpart
    if not cp:
        return ""
    cp_latin = cp.get("latin", "")
    cp_common = (cp.get("common") or [None])[0] or cp_latin
    if not cp_latin:
        return ""
    return (
        "\n**Critical distinction (do not skip):** _%s_ is a DIFFERENT species from the commonly-kept "
        "%s (_%s_). Many rules exempt \"domestic\" or \"tame\" versions of this animal, but such an "
        "exemption is often written to name only %s / _%s_. Determine specifically whether any such "
        "exemption applies to _%s_, or only to the counterpart species — do not assume it covers our "
        "species; find the text.\n"
        % (
            cfg.species_latin,
            cp_common,
            cp_latin,
            cp_common,
            cp_latin,
            cfg.species_latin,
        )
    )


def activities_block():
    """Numbered activity list for {{ACTIVITIES}}, from config (default keep/breed/sell_give/transport)."""
    labels = {
        "keep": "**KEEP / own** a %s as a pet" % cfg.species_common,
        "breed": "**BREED** %ss" % cfg.species_common,
        "sell_give": "**SELL or GIVE AWAY** %ss" % cfg.species_common,
        "transport": (
            "**TRANSPORT** %ss (within the jurisdiction; import into it; export, "
            "interstate, or international as relevant)" % cfg.species_common
        ),
    }
    lines = []
    for i, act in enumerate(cfg.activities, 1):
        label = labels.get(act, "**%s** the animal" % act.upper().replace("_", "/"))
        lines.append("%d. %s" % (i, label))
    return "\n".join(lines)


def fill_template(body, desc):
    """Substitute every placeholder in the prompt body."""
    out = body
    out = out.replace("{{JURISDICTION}}", desc)
    out = out.replace("{{SPECIES_LATIN}}", cfg.species_latin)
    out = out.replace("{{SPECIES_COMMON_ALL}}", ", ".join(cfg.species_common_all()) or cfg.species_common)
    out = out.replace("{{SPECIES_COMMON}}", cfg.species_common)
    out = out.replace("{{COUNTERPART_BLOCK}}", counterpart_block())
    out = out.replace("{{ACTIVITIES}}", activities_block())
    return out


def found_block(d):
    """Build the 'What we already found' seed from the JSON."""
    j = d.get("jurisdiction", {})
    lines = [
        "",
        "---",
        "",
        "## What we already found (PRELIMINARY web research — VERIFY and CORRECT each point against "
        "official sources; overturn it if wrong):",
        "",
    ]
    summ = (d.get("summary") or "").strip()
    if summ:
        lines += ["**Our working summary:** " + summ, ""]
    lines.append(
        "**Per-activity (our preliminary read — confirm the status + the operative law, or correct it):**"
    )
    acts = d.get("activities") or {}
    for act in cfg.activities:
        a = acts.get(act)
        if not a:
            continue
        why = (a.get("why") or "").strip()
        gl = (a.get("governing_law") or "").strip()
        lines.append(
            "- **%s** — our read: `%s` (confidence %s). Why: %s%s"
            % (
                act.upper().replace("_", "/"),
                a.get("status", "?"),
                a.get("confidence", "?"),
                why,
                (" [Law: %s]" % gl) if gl else "",
            )
        )
    lines.append("")
    foc = (d.get("inquiry_focus") or "").strip()
    if foc:
        lines += ["**Specific open questions we most need resolved:** " + foc, ""]
    # local terms (live on the jurisdiction sub-object)
    terms = j.get("local_terms") or []
    if terms:
        lines += ["**Local/legal terms to search:** " + ", ".join(terms), ""]
    # contact (primary, else first)
    contacts = d.get("contacts") or []
    if contacts:
        c = next((x for x in contacts if x.get("primary")), contacts[0])
        bits = [b for b in [c.get("agency"), c.get("email"), c.get("form_url"), c.get("phone")] if b]
        if bits:
            lines += [
                "**Authoritative agency we identified (confirm + improve the contact if you can):** "
                + " | ".join(bits),
                "",
            ]
    # sources we already have
    srcs = d.get("sources") or []
    if srcs:
        lines.append("**Sources we already used (verify these are current + find any we missed):**")
        for s in srcs[:12]:
            t = s.get("title", "")
            u = s.get("url", "")
            au = s.get("authority", "")
            lines.append("- %s — %s — %s" % (t, au, u))
        lines.append("")
    return "\n".join(lines)


def main():
    cfg.ensure_dirs()
    if not os.path.exists(TEMPLATE):
        raise SystemExit("ERROR: %s not found" % TEMPLATE)
    tmpl = open(TEMPLATE, encoding="utf-8").read()
    # use only the prompt body (everything after the first '---' separator under the how-to-use header)
    if "\n---\n" in tmpl:
        body = tmpl.split("\n---\n", 1)[1].strip()
    else:
        body = tmpl.strip()

    have = existing_prompt_ids()
    written, skipped = [], 0
    out_dir = cfg.prompts_dir()
    for f in sorted(glob.glob(os.path.join(cfg.data_dir(), "*.json"))):
        jid = os.path.splitext(os.path.basename(f))[0]
        try:
            d = json.load(open(f, encoding="utf-8"))
        except json.JSONDecodeError as e:
            sys.stderr.write("  [skip] %s — invalid JSON: %s\n" % (jid, e))
            continue
        if not is_preliminary(d):
            continue
        if jid in have:
            skipped += 1
            continue
        desc = descriptor(d.get("jurisdiction", {}))
        name = d.get("jurisdiction", {}).get("name", jid)
        prompt = (
            "# Deep-Research prompt — %s (%s)\n\n" % (name, jid)
            + fill_template(body, desc)
            + "\n"
            + found_block(d)
        )
        out = os.path.join(out_dir, jid + ".md")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(prompt)
        written.append(jid)

    print("Wrote %d new DR prompt(s); skipped %d (already had one)." % (len(written), skipped))
    if written:
        print("New prompts:", ", ".join(written))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()

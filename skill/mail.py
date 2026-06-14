# -*- coding: utf-8 -*-
"""Pet Freedom — agency-inquiry SENDER + reply reader (OPTIONAL module; off by default).

FILE-BASED: the queue is data/inquiries.json (written by skill/inquiries.py) and the local mailbox
dedupe state is data/.mail_state.json. The companion plugin is NOT required.

Mail credentials come from .env (via common.load_env):
  SITE_MAIL_USER, SITE_MAIL_PASS, SITE_SMTP_HOST, SITE_SMTP_PORT (default 465),
  SITE_IMAP_HOST (falls back to SMTP host), SITE_IMAP_PORT (default 993).
The actual From-address is SITE_MAIL_USER — read at runtime, never hard-coded. Authenticated SMTP keeps
it SPF/DKIM-aligned and credible.

Keeping a record of what you send: SMTP sending and the IMAP "Sent" folder are separate, so a plain
script leaves no trace in webmail. Every send here is therefore recorded two ways: a durable local copy
(data/sent_archive/*.eml + an index line in data/sent_log.jsonl) that does NOT depend on your mail server,
and — unless your provider auto-saves sent mail — a copy appended to your mailbox's Sent folder so it also
shows in webmail. Providers differ (Sent-folder name, special-use support, some auto-save and would create
a duplicate), so run `verify` first and tune two optional .env settings if needed:
  SITE_MAIL_SENT_FOLDER   exact Sent-folder name if auto-detection fails (e.g. "INBOX.Sent")
  SITE_MAIL_COPY_TO_SENT  auto (default) | always | never   (use 'never' on Gmail/Outlook, which auto-save)

Safety contract:
  - Only channel=="email" AND status=="approved" inquiries are ever sent. Web-form inquiries are never
    auto-sent (submit them by hand at their form URL).
  - HARD GUARD: anything already status=="sent" (or carrying a sent_at) is skipped unless --resend.
  - config.inquiries.confirm_each (default true): before sending each message the full draft is shown and
    an explicit interactive "yes" is required. In --dry mode the draft is shown but nothing is sent.
  - Recipients are never invented — we only send to the "to" address already in the queue.

Usage:
  python skill/mail.py verify               # check SMTP+IMAP login + Sent-folder handling (sends nothing)
  python skill/mail.py list                 # show the queue (status / channel / lang / jurisdiction / agency / target)
  python skill/mail.py approve <key>        # mark an inquiry approved (ready to send)
  python skill/mail.py send [--dry] [--resend]   # send approved email inquiries (confirm_each honored; archives each)
  python skill/mail.py fetch                # read INBOX, print messages not seen before (never sets \\Seen)
  python skill/mail.py answer <key>         # paste an agency reply (EOF / Ctrl-Z Enter), mark answered + store
  python skill/mail.py sent                 # show the local record of everything we've sent
"""
import os
import sys
import ssl
import re
import time
import json
import smtplib
import imaplib
import email
import datetime
from email.message import EmailMessage
from email.header import decode_header, make_header
from email.utils import formatdate, make_msgid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import config  # noqa: E402
from common import load_env  # noqa: E402


def _queue_path(cfg):
    """data/inquiries.json — sibling of data/jurisdictions/."""
    return os.path.join(os.path.dirname(cfg.data_dir()), "inquiries.json")


def _state_path(cfg):
    """data/.mail_state.json — IMAP dedupe state (seen Message-IDs)."""
    return os.path.join(os.path.dirname(cfg.data_dir()), ".mail_state.json")


def _sent_archive_dir(cfg):
    """data/sent_archive/ — one .eml per sent message (durable, server-independent record)."""
    return os.path.join(os.path.dirname(cfg.data_dir()), "sent_archive")


def _sent_log_path(cfg):
    """data/sent_log.jsonl — append-only index of everything we have sent."""
    return os.path.join(os.path.dirname(cfg.data_dir()), "sent_log.jsonl")


def load_queue(cfg):
    path = _queue_path(cfg)
    if not os.path.exists(path):
        raise SystemExit(
            "No inquiry queue at %s\n  -> run: python skill/inquiries.py  (with config.inquiries.enabled = true)" % path
        )
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else []


def save_queue(cfg, items):
    path = _queue_path(cfg)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


def update_item(cfg, key, **fields):
    """Patch the queue item with this key; returns True if found + written."""
    items = load_queue(cfg)
    hit = False
    for q in items:
        if q.get("key") == key:
            q.update(fields)
            hit = True
    if hit:
        save_queue(cfg, items)
    return hit


def mail_cfg():
    """Mail settings from .env, with sensible defaults. SITE_IMAP_HOST falls back to SITE_SMTP_HOST."""
    e = load_env()
    missing = [k for k in ("SITE_MAIL_USER", "SITE_MAIL_PASS", "SITE_SMTP_HOST") if not e.get(k)]
    if missing:
        raise SystemExit(
            "Mailbox not configured. Add to .env: " + ", ".join(missing) +
            "\n(See .env.example and docs/EMAIL-DELIVERABILITY.md — use a real authenticated mailbox on your domain.)"
        )
    return {
        "user": e["SITE_MAIL_USER"],
        "pass": e["SITE_MAIL_PASS"],
        "smtp_host": e["SITE_SMTP_HOST"],
        "smtp_port": int(e.get("SITE_SMTP_PORT") or "465"),
        "imap_host": e.get("SITE_IMAP_HOST") or e["SITE_SMTP_HOST"],
        "imap_port": int(e.get("SITE_IMAP_PORT") or "993"),
        # how to keep a Sent-folder copy: auto (default) | always | never. 'never' for providers that
        # auto-save sent mail (Gmail/Outlook) to avoid duplicates. Local archive is kept regardless.
        "copy_to_sent": (e.get("SITE_MAIL_COPY_TO_SENT") or "auto").strip().lower(),
        # explicit Sent-folder name if auto-detection cannot find it (e.g. "INBOX.Sent").
        "sent_folder": (e.get("SITE_MAIL_SENT_FOLDER") or "").strip(),
    }


# ── commands ──

def cmd_list(cfg):
    items = load_queue(cfg)
    if not items:
        print("Queue is empty. Run: python skill/inquiries.py")
        return
    for q in items:
        tgt = "<%s>" % q.get("to") if q.get("to") else "(form: %s)" % q.get("form_url", "")
        print("[%-8s] %-8s %-2s %-16s %s %s" % (
            q.get("status", ""), q.get("channel", ""), q.get("language", ""),
            (q.get("jurisdiction", "") or "")[:16], q.get("agency", ""), tgt))
        print("          key: %s" % q.get("key"))
    forms = [q for q in items if q.get("channel") == "web_form"
             and q.get("status") not in ("answered", "skipped")]
    if forms:
        print("\nWEB-FORM inquiries need MANUAL submission (never auto-sent):")
        for q in forms:
            print("  - %s (%s) -> %s" % (q.get("jurisdiction"), q.get("language"), q.get("form_url")))


def cmd_approve(cfg, key):
    print("approved" if update_item(cfg, key, status="approved") else "not found", key)


def cmd_answer(cfg, key):
    print("Paste the agency reply, then EOF (Ctrl-Z Enter on Windows, Ctrl-D on macOS/Linux):")
    reply = sys.stdin.read().strip()
    ok = update_item(cfg, key, status="answered", reply=reply)
    print("answered" if ok else "not found", key)


def _confirm(prompt):
    """Interactive yes/no; anything other than an explicit 'yes'/'y' is a no."""
    try:
        ans = input(prompt).strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def _show_draft(q):
    print("=" * 70)
    print("TO:   %s" % q.get("to"))
    print("SUBJ: %s" % q.get("subject"))
    print("LANG: %-3s  JURISDICTION: %s  AGENCY: %s" % (
        q.get("language"), q.get("jurisdiction"), q.get("agency")))
    print("-" * 70)
    print((q.get("body") or "").strip())
    print("=" * 70)


def send_one(mc, to, subject, body):
    """Send via authenticated SMTP and return the exact EmailMessage that went out (Date + Message-ID
    set) so the caller can archive a faithful copy."""
    msg = EmailMessage()
    msg["From"] = mc["user"]
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = mc["user"]
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=mc["user"].split("@")[-1])
    msg.set_content(body)
    ctx = ssl.create_default_context()
    if mc["smtp_port"] == 465:
        with smtplib.SMTP_SSL(mc["smtp_host"], mc["smtp_port"], context=ctx, timeout=30) as s:
            s.login(mc["user"], mc["pass"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(mc["smtp_host"], mc["smtp_port"], timeout=30) as s:
            s.starttls(context=ctx)
            s.login(mc["user"], mc["pass"])
            s.send_message(msg)
    return msg


# Providers that already save SMTP-sent mail to "Sent" themselves; appending would duplicate it.
_AUTOSAVE_HINTS = ("gmail", "googlemail", "google", "outlook", "office365", "hotmail", "live.", "microsoft")


def _provider_autosaves(host):
    h = (host or "").lower()
    return any(k in h for k in _AUTOSAVE_HINTS)


def _detect_sent_folder(M, override=""):
    """Return the mailbox's Sent folder: an explicit override, else the special-use \\Sent box, else a
    common name. Returns None if it cannot be determined (caller should NOT guess blindly)."""
    if override:
        return override
    try:
        typ, boxes = M.list()
        if typ == "OK" and boxes:
            fallback = None
            for b in boxes:
                line = b.decode("utf-8", "replace") if isinstance(b, bytes) else str(b)
                m = re.search(r'"([^"]*)"\s*$', line)
                name = m.group(1) if m else line.split()[-1].strip('"')
                if "\\Sent" in line:
                    return name
                if name.lower() in ("sent", "inbox.sent", "sent items", "inbox.sent items", "[gmail]/sent mail"):
                    fallback = fallback or name
            return fallback
    except Exception:
        pass
    return None


def archive_sent(cfg, mc, msg, meta):
    """Durable record of a sent message. ALWAYS writes a local .eml + a sent_log.jsonl line. Then, unless
    the provider auto-saves or copy_to_sent='never', appends a copy to the mailbox Sent folder so it also
    shows in webmail. Returns a human-readable description of what was recorded."""
    arch = _sent_archive_dir(cfg)
    os.makedirs(arch, exist_ok=True)
    tag = re.sub(r"[^A-Za-z0-9._-]+", "-", "%s_%s" % (meta.get("jurisdiction", ""), meta.get("key", ""))).strip("-")
    fn = "%s_%s.eml" % (datetime.date.today().isoformat(), tag or "message")
    with open(os.path.join(arch, fn), "wb") as fh:
        fh.write(bytes(msg))
    with open(_sent_log_path(cfg), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "sent_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "to": msg["To"], "subject": msg["Subject"], "message_id": msg["Message-ID"],
            "key": meta.get("key"), "jurisdiction": meta.get("jurisdiction"), "eml": fn,
        }, ensure_ascii=False) + "\n")
    mode = mc.get("copy_to_sent", "auto")
    if mode == "never":
        return "local archive only (SITE_MAIL_COPY_TO_SENT=never)"
    if mode == "auto" and _provider_autosaves(mc["imap_host"]):
        return ("local archive only (provider likely auto-saves to Sent; "
                "set SITE_MAIL_COPY_TO_SENT=always to force a copy)")
    try:
        M = imaplib.IMAP4_SSL(mc["imap_host"], mc["imap_port"])
        M.login(mc["user"], mc["pass"])
        folder = _detect_sent_folder(M, mc.get("sent_folder", ""))
        if not folder:
            M.logout()
            return "local archive only (no Sent folder detected; set SITE_MAIL_SENT_FOLDER to its exact name)"
        M.append(folder, "(\\Seen)", imaplib.Time2Internaldate(time.time()), bytes(msg))
        M.logout()
        return "Sent folder '%s' + local archive" % folder
    except Exception as ex:  # noqa: BLE001
        return "local archive only (IMAP Sent copy failed: %s)" % ex


def cmd_send(cfg, dry, resend):
    items = load_queue(cfg)
    approved = [q for q in items if q.get("channel") == "email" and q.get("status") == "approved"]
    # HARD GUARD: never re-email anything already sent (status sent OR a sent_at date) unless --resend.
    queue = []
    for q in approved:
        if (q.get("status") == "sent" or q.get("sent_at")) and not resend:
            print("SKIP (already sent %s) -> %s  [use --resend to force a duplicate]" % (
                q.get("sent_at") or "?", q.get("jurisdiction")))
            continue
        queue.append(q)
    if not queue:
        print("Nothing to send.")
        return

    confirm_each = cfg.confirm_each
    mc = None if dry else mail_cfg()
    sent_count = 0
    for q in queue:
        if confirm_each or dry:
            _show_draft(q)
        if dry:
            print("[dry] would send to %s" % q.get("to"))
            continue
        if confirm_each and not _confirm("Send this inquiry? type 'yes' to send: "):
            print("skipped (not confirmed) -> %s" % q.get("jurisdiction"))
            continue
        try:
            msg = send_one(mc, q["to"], q["subject"], q["body"])
            where = archive_sent(cfg, mc, msg, q)
            update_item(cfg, q["key"], status="sent", sent_at=datetime.date.today().isoformat())
            sent_count += 1
            print("SENT -> %s  (%s)  [recorded: %s]" % (q["to"], q.get("jurisdiction"), where))
        except Exception as ex:  # noqa: BLE001 - surface the failure, keep going
            print("FAILED -> %s: %s" % (q.get("to"), ex))
    if not dry:
        print("\n%d message(s) sent." % sent_count)


def _decode(h):
    try:
        return str(make_header(decode_header(h or "")))
    except Exception:
        return h or ""


def _body_of(m):
    if m.is_multipart():
        for part in m.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload is not None:
                    return payload.decode(part.get_content_charset() or "utf-8", "replace")
        return ""
    payload = m.get_payload(decode=True)
    if payload is None:
        return ""
    return payload.decode(m.get_content_charset() or "utf-8", "replace")


def cmd_fetch(cfg):
    mc = mail_cfg()
    state_path = _state_path(cfg)
    seen = set()
    if os.path.exists(state_path):
        try:
            with open(state_path, encoding="utf-8") as fh:
                seen = set(json.load(fh).get("seen", []))
        except (OSError, ValueError):
            seen = set()

    M = imaplib.IMAP4_SSL(mc["imap_host"], mc["imap_port"])
    M.login(mc["user"], mc["pass"])
    M.select("INBOX")
    # search ALL (never rely on / set \Seen); we dedupe ourselves by Message-ID.
    _, data = M.search(None, "ALL")
    new = 0
    for num in data[0].split():
        # BODY.PEEK so the server does NOT mark the message \Seen.
        _, d = M.fetch(num, "(BODY.PEEK[])")
        m = email.message_from_bytes(d[0][1])
        mid = m.get("Message-ID", num.decode())
        if mid in seen:
            continue
        seen.add(mid)
        new += 1
        print("=" * 70)
        print("FROM: %s\nSUBJ: %s\nDATE: %s" % (
            _decode(m.get("From", "")), _decode(m.get("Subject", "")), m.get("Date", "")))
        print("-" * 70)
        print(_body_of(m).strip()[:3000])
    M.logout()

    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump({"seen": sorted(seen)}, fh)
    print("=" * 70)
    print("%d new message(s). To record a reply: python skill/mail.py answer <key>" % new)


def cmd_sent(cfg):
    """Show the local record of everything we have sent (newest last)."""
    path = _sent_log_path(cfg)
    if not os.path.exists(path):
        print("No sent record yet. The next `send` will log here:\n  %s" % path)
        return
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    for r in rows:
        print("%-19s  %-16s -> %-32s %s" % (
            str(r.get("sent_at", ""))[:19], (r.get("jurisdiction", "") or "")[:16],
            r.get("to", "") or "", r.get("subject", "") or ""))
    print("\n%d message(s) on record. Full .eml copies in:\n  %s" % (len(rows), _sent_archive_dir(cfg)))


def cmd_verify(cfg):
    """Check the mailbox WITHOUT sending anything: SMTP login, IMAP login, Sent-folder detection, and how
    the Sent copy will behave on THIS provider (some auto-save and would otherwise duplicate)."""
    mc = mail_cfg()
    ok = True
    ctx = ssl.create_default_context()
    try:
        if mc["smtp_port"] == 465:
            with smtplib.SMTP_SSL(mc["smtp_host"], mc["smtp_port"], context=ctx, timeout=30) as s:
                s.login(mc["user"], mc["pass"]); s.noop()
        else:
            with smtplib.SMTP(mc["smtp_host"], mc["smtp_port"], timeout=30) as s:
                s.starttls(context=ctx); s.login(mc["user"], mc["pass"]); s.noop()
        print("SMTP   OK    login %s @ %s:%s" % (mc["user"], mc["smtp_host"], mc["smtp_port"]))
    except Exception as ex:  # noqa: BLE001
        ok = False
        print("SMTP   FAIL  %s" % ex)
    folder = None
    try:
        M = imaplib.IMAP4_SSL(mc["imap_host"], mc["imap_port"])
        M.login(mc["user"], mc["pass"])
        folder = _detect_sent_folder(M, mc.get("sent_folder", ""))
        M.logout()
        print("IMAP   OK    login %s @ %s:%s" % (mc["user"], mc["imap_host"], mc["imap_port"]))
    except Exception as ex:  # noqa: BLE001
        ok = False
        print("IMAP   FAIL  %s" % ex)
    mode = mc.get("copy_to_sent", "auto")
    print("SENT   detected folder: %s" % (folder or "(none)"))
    if mode == "never":
        plan = "copy-to-Sent is OFF (SITE_MAIL_COPY_TO_SENT=never). Local archive only."
    elif mode == "auto" and _provider_autosaves(mc["imap_host"]):
        plan = ("provider looks like it AUTO-SAVES sent mail, so 'auto' will SKIP the IMAP copy to avoid a "
                "duplicate (local archive only). Set SITE_MAIL_COPY_TO_SENT=always to force a copy anyway.")
    elif not folder:
        plan = ("no Sent folder detected. Local archive only. Set SITE_MAIL_SENT_FOLDER to your Sent folder's "
                "exact name (check your webmail) to enable the in-mailbox copy.")
    else:
        plan = "each send will append a copy to Sent folder '%s' (and always keep the local archive)." % folder
    print("PLAN   %s" % plan)
    try:
        os.makedirs(_sent_archive_dir(cfg), exist_ok=True)
        print("LOCAL  OK    durable archive dir is writable: %s" % _sent_archive_dir(cfg))
    except Exception as ex:  # noqa: BLE001
        ok = False
        print("LOCAL  FAIL  cannot write archive dir: %s" % ex)
    print("\n%s" % ("All good. Sending will keep a full record." if ok else "Fix the FAIL items above before sending."))


def main():
    cfg = config.load()
    if not cfg.inquiries_enabled:
        print("Inquiries module is OFF (config.inquiries.enabled = false). Enable it in config.json first.")
        return
    args = sys.argv[1:]
    cmd = args[0] if args else "list"
    if cmd == "list":
        cmd_list(cfg)
    elif cmd == "verify":
        cmd_verify(cfg)
    elif cmd == "approve" and len(args) > 1:
        cmd_approve(cfg, args[1])
    elif cmd == "answer" and len(args) > 1:
        cmd_answer(cfg, args[1])
    elif cmd == "send":
        cmd_send(cfg, "--dry" in args, "--resend" in args)
    elif cmd == "fetch":
        cmd_fetch(cfg)
    elif cmd == "sent":
        cmd_sent(cfg)
    else:
        raise SystemExit(
            "usage: skill/mail.py verify | list | approve <key> | answer <key> | send [--dry] [--resend] | fetch | sent")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Pet Freedom — agency-inquiry SENDER + reply reader (OPTIONAL module; off by default).

FILE-BASED: the queue is data/inquiries.json (written by skill/inquiries.py) and the local mailbox
dedupe state is data/.mail_state.json. The companion plugin is NOT required.

Mail credentials come from .env (via common.load_env):
  SITE_MAIL_USER, SITE_MAIL_PASS, SITE_SMTP_HOST, SITE_SMTP_PORT (default 465),
  SITE_IMAP_HOST (falls back to SMTP host), SITE_IMAP_PORT (default 993).
The actual From-address is SITE_MAIL_USER — read at runtime, never hard-coded. Authenticated SMTP keeps
it SPF/DKIM-aligned and credible.

Safety contract:
  - Only channel=="email" AND status=="approved" inquiries are ever sent. Web-form inquiries are never
    auto-sent (submit them by hand at their form URL).
  - HARD GUARD: anything already status=="sent" (or carrying a sent_at) is skipped unless --resend.
  - config.inquiries.confirm_each (default true): before sending each message the full draft is shown and
    an explicit interactive "yes" is required. In --dry mode the draft is shown but nothing is sent.
  - Recipients are never invented — we only send to the "to" address already in the queue.

Usage:
  python skill/mail.py list                 # show the queue (status / channel / lang / jurisdiction / agency / target)
  python skill/mail.py approve <key>        # mark an inquiry approved (ready to send)
  python skill/mail.py send [--dry] [--resend]   # send approved email inquiries (confirm_each honored)
  python skill/mail.py fetch                # read INBOX, print messages not seen before (never sets \\Seen)
  python skill/mail.py answer <key>         # paste an agency reply (EOF / Ctrl-Z Enter), mark answered + store
"""
import os
import sys
import ssl
import json
import smtplib
import imaplib
import email
import datetime
from email.message import EmailMessage
from email.header import decode_header, make_header

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
    msg = EmailMessage()
    msg["From"] = mc["user"]
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = mc["user"]
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
            send_one(mc, q["to"], q["subject"], q["body"])
            update_item(cfg, q["key"], status="sent", sent_at=datetime.date.today().isoformat())
            sent_count += 1
            print("SENT -> %s  (%s)" % (q["to"], q.get("jurisdiction")))
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


def main():
    cfg = config.load()
    if not cfg.inquiries_enabled:
        print("Inquiries module is OFF (config.inquiries.enabled = false). Enable it in config.json first.")
        return
    args = sys.argv[1:]
    cmd = args[0] if args else "list"
    if cmd == "list":
        cmd_list(cfg)
    elif cmd == "approve" and len(args) > 1:
        cmd_approve(cfg, args[1])
    elif cmd == "answer" and len(args) > 1:
        cmd_answer(cfg, args[1])
    elif cmd == "send":
        cmd_send(cfg, "--dry" in args, "--resend" in args)
    elif cmd == "fetch":
        cmd_fetch(cfg)
    else:
        raise SystemExit(
            "usage: skill/mail.py list | approve <key> | answer <key> | send [--dry] [--resend] | fetch")


if __name__ == "__main__":
    main()

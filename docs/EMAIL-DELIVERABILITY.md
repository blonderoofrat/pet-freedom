# EMAIL-DELIVERABILITY — so your agency inquiries don't bounce

You only need this if you turn on the optional **inquiries** module. When you do, this is the single hardest
setup step — and the most important. Government and large mail systems are strict: if your mail isn't
**authenticated**, they may silently drop it or bounce it, and your inquiry never arrives.

The fix is three DNS records working together: **SPF, DKIM, and DMARC.** Set them up once, verify, and your
mail lands.

> This guide is **host-agnostic**. The worked example near the bottom uses **placeholder** values only —
> swap in your own everywhere you see `example.com`.

---

## Why all three matter

Think of it as three questions a receiving mail server asks about a message claiming to be from your domain:

- **SPF (Sender Policy Framework)** — *"Is this server allowed to send mail for this domain?"*
  An SPF record is a TXT record listing the hosts/services permitted to send as your domain. If your sending
  host isn't listed, SPF fails.

- **DKIM (DomainKeys Identified Mail)** — *"Was this message really signed by the domain, and unaltered?"*
  Your mail host signs outgoing mail with a private key; you publish the matching public key in DNS. The
  receiver verifies the signature. If it's missing or doesn't match, DKIM fails.

- **DMARC (Domain-based Message Authentication, Reporting & Conformance)** — *"If SPF/DKIM don't line up
  with the visible From: address, what should I do?"*
  DMARC ties SPF/DKIM to the From: domain (*alignment*) and tells receivers your policy (`none` = monitor,
  `quarantine` = spam folder, `reject` = bounce). Without DMARC, strict receivers may distrust you by
  default.

Any one alone is weak. Together they prove the mail is genuinely from you and wasn't tampered with — which is
exactly what a government mail filter wants before it trusts a stranger's message.

---

## General steps (any host)

1. **Use a real mailbox on your own domain.** Send from `you@example.com`, *not* a free
   `@gmail.com`/`@outlook.com` address, and not a made-up address. Inquiries should come from a mailbox you
   actually monitor (replies come back to it).

2. **Publish an SPF record** that includes your sending host. One TXT record at your root domain:

   ```dns
   example.com.   TXT   "v=spf1 include:_spf.YOUR-MAIL-HOST.example -all"
   ```

   Use the exact `include:` your host documents. Keep it to **one** SPF record; `-all` (hard fail) is
   strongest, `~all` (soft fail) is more forgiving while you test.

3. **Enable DKIM** in your mail host's control panel. It generates a key pair and gives you a TXT (or CNAME)
   record to publish at a selector hostname:

   ```dns
   SELECTOR._domainkey.example.com.   TXT   "v=DKIM1; k=rsa; p=YOUR-PUBLIC-KEY"
   ```

   The `SELECTOR` and exact value come from your host. Publish it, then turn on signing.

4. **Add a DMARC record.** One TXT record at `_dmarc`:

   ```dns
   _dmarc.example.com.   TXT   "v=DMARC1; p=none; rua=mailto:dmarc@example.com"
   ```

   Start with `p=none` to monitor (and collect the `rua` aggregate reports), then tighten to
   `p=quarantine` and eventually `p=reject` once SPF+DKIM pass cleanly.

5. **Verify before you send anything real.** Send a test message to a checker like **mail-tester.com**
   (it gives you a one-time address and scores SPF, DKIM, DMARC, and content) or use Google Admin Toolbox /
   `dig` to confirm the records resolve. Aim for SPF **pass**, DKIM **pass**, DMARC **pass/aligned**. DNS can
   take up to ~24–48h to propagate.

6. **Send conservatively.** Real, individualized inquiries to real agencies — not bulk. The skill confirms
   each one before sending (`confirm_each`), which also keeps your volume and reputation healthy.

---

## Example: SiteGround mailbox + Cloudflare DNS (SANITIZED — placeholders only)

A worked example to make the steps concrete. **Every value below is a placeholder** — substitute your own
domain, selector, and keys. This mirrors a common setup (email hosted at one provider, DNS at another) and is
**not** real credentials or a real domain.

> Setup: mailbox lives at your **host** (here, generically "SiteGround"); DNS is managed at **Cloudflare**.
> The three records all get added in Cloudflare, using values your mail host gives you.

1. **Create the mailbox** in your host's Email panel: `you@example.com`. Note the SMTP/IMAP host and ports
   your host shows (commonly SMTP `465` SSL, IMAP `993` SSL). Put these in `.env`:

   ```ini
   SITE_MAIL_USER=you@example.com
   SITE_MAIL_PASS=your-mailbox-password
   SITE_SMTP_HOST=mail.example.com
   SITE_SMTP_PORT=465
   SITE_IMAP_HOST=mail.example.com
   SITE_IMAP_PORT=993
   ```

2. **SPF** — in Cloudflare DNS, add a TXT record (proxy/orange-cloud does **not** apply to TXT — it's
   DNS-only):

   | Type | Name | Content |
   |---|---|---|
   | TXT | `@` | `v=spf1 include:_spf.YOUR-MAIL-HOST.example -all` |

3. **DKIM** — turn on DKIM in your host's Email Authentication settings; it gives you a selector + public
   key. Add it in Cloudflare:

   | Type | Name | Content |
   |---|---|---|
   | TXT | `SELECTOR._domainkey` | `v=DKIM1; k=rsa; p=YOUR-PUBLIC-KEY` |

   (Some hosts give a CNAME instead — add it exactly as shown by the host.)

4. **DMARC** — add in Cloudflare:

   | Type | Name | Content |
   |---|---|---|
   | TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@example.com` |

5. **Verify** with mail-tester.com (send your test from `you@example.com`). When SPF/DKIM/DMARC all pass,
   tighten DMARC to `p=quarantine` then `p=reject`.

> Reminder: nothing above is real — `example.com`, `SELECTOR`, `YOUR-MAIL-HOST`, and `YOUR-PUBLIC-KEY` are
> placeholders. Never commit real mailbox passwords or keys; they belong in `.env` (gitignored) and your DNS
> panel only.

---

## Got another host working? Share the recipe

This worked example is one of many possible setups. If you get a different host/DNS combination working
(Gmail/Workspace, Fastmail, Zoho, Namecheap, cPanel + Route 53, …), please contribute a sanitized recipe to
**[`recipes/`](recipes/)** — same shape as above, **placeholder values only, no real domains/keys**. It saves
the next person the hardest step.

---

*Deliverability is the one place where "it works on my machine" can quietly fail in the field. Verify with a
checker before you trust it — and remember this is plumbing for a research aid, not legal advice.*

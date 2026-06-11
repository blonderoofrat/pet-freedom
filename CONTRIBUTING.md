# Contributing to Pet Freedom

Thanks for helping animals and the people who love them. A few ground rules keep this resource trustworthy.

## Responsible use (please read)
- **This is a research aid, not legal advice.** If you publish information produced with this tool, *you* are
  responsible for its accuracy and for following your local laws.
- **Be honest about confidence.** Never present a guess as a confirmed answer. Use the `unregulated_unclear` /
  `needs_verification` states; show the "preliminary" banner until something is verified.
- **Never impersonate an official**, and never fabricate a citation. Every status must trace to a real source.
- **Respect agencies' time.** Before emailing an agency, check whether the question is already answered in the seed
  data. Prefer the general office channel over an individual's inbox. Send only when a real gap exists, and always
  with a human confirming each message.
- **Protect privacy.** Never commit secrets (`.env`), your `config.json`, or your working `data/`. Public pages must
  render only public-safe fields (the build already enforces this).

## Ways to contribute
- **Host recipes** (`docs/recipes/`): a short, sanitized how-to for setting up authenticated email + SPF/DKIM/DMARC
  on your host (e.g. SiteGround, Cloudflare, Google Workspace, Fastmail). No secrets — just the steps.
- **Jurisdiction packs** (`starter-packs/`): structural lists (ids/levels/parents/slugs) for regions we don't cover.
- **Seed corrections**: if a bundled jurisdiction fact is out of date or wrong, open an issue/PR with the current
  official source. Laws change; we want the seed to age gracefully.
- **Localization**: additional inquiry-template languages (`templates/inquiry/`).
- **Code**: bug fixes and new modules (keep the render-only-public OPSEC discipline intact).

## What NOT to contribute
- Any real person's private data; any individual's contact who is **not** a government official acting in their
  official capacity; credentials of any kind; scraped or copyrighted statute text (link to the official source
  instead).

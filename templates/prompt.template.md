# Deep-Research prompt — per-jurisdiction template

**How to use:** this file has two parts separated by the `---` below. Everything *above* the separator is
guidance for you (the operator) and is ignored by the generator. Everything *below* is the prompt body, with
`{{PLACEHOLDERS}}` that `skill/make_prompts.py` fills in from `config.json` and each jurisdiction's data:

- `{{JURISDICTION}}` — the descriptor (e.g. "the U.S. state of Florida", "the Canadian province of Ontario", or a country name).
- `{{SPECIES_LATIN}}` — the species' scientific name (from `species.latin`).
- `{{SPECIES_COMMON}}` — the primary common name (from `species.common[0]`).
- `{{SPECIES_COMMON_ALL}}` — all common names, comma-joined (from `species.common`).
- `{{COUNTERPART_BLOCK}}` — the "different species from the commonly-kept counterpart" nuance, present only when a counterpart is configured (empty otherwise).
- `{{ACTIVITIES}}` — the numbered activity list to analyze (from `activities`).

To run a single jurisdiction by hand, copy the body below, substitute the placeholders, and paste it into your
Deep-Research tool (Gemini Pro Deep Research, Claude deep-research, etc.). The generator does this for you in bulk
and appends a "What we already found" section so the engine confirms or overturns the working answer. Paste the
result back to the agent; it verifies against the official sources, structures it into `data/jurisdictions/<id>.json`,
and assigns confidence. Keep one filled copy per jurisdiction for provenance.

---

You are helping build an accurate, source-cited reference on the legal status of keeping **domesticated
{{SPECIES_COMMON}}**. Research the **official law of {{JURISDICTION}}** as it applies to the species
**_{{SPECIES_LATIN}}_** (also known as: {{SPECIES_COMMON_ALL}}).
{{COUNTERPART_BLOCK}}
**Lens — assume a pathway:** your goal is to find the **least-restrictive lawful pathway** by which a private
person could keep, and where possible breed, transfer, and move this animal — not merely to report the first
prohibition you find. A species being classified as wild, non-native, or a pest does **not** by itself make a
captive-bred pet illegal; distinguish the **wild/pest classification** of the species from the rules that apply
to an **individual captive-bred animal in a private home**. Where a permit, registration, or exemption could make
an activity lawful, find and describe that route. Reserve a "prohibited" reading for cases where there is genuinely
no lawful pathway, and say what you searched to conclude that.

For {{JURISDICTION}}, analyze these activities **separately**:
{{ACTIVITIES}}

For **each** activity, provide:
- **Status**, choosing one: `Legal` · `Legal with a permit/license` · `Restricted` · `Prohibited` · `Unregulated/unclear`.
- **Why** — quote or closely paraphrase the operative language of the governing statute/regulation/agency rule.
- **Governing authority** — the exact statute or rule citation + the agency, with a **direct URL to the
  official source** (prefer the government or legislative site; use secondary legal databases only to corroborate).
- **Confidence** (high / medium / low) and exactly **what is ambiguous or unconfirmed**.

Also report:
- **Restrictions:** registration, permit/license, health testing, veterinary/health certificate,
  caging/facility standards, inspections — and whether each applies to the **person**, the **animals**, or
  both. Include form names, where to file, and fees if stated.
- **Commercial layer (separate from possession):** is there a distinct **breeder / dealer / animal-business
  license** that applies to BREEDING or SELLING even where merely KEEPING the animal is unregulated? Note any
  small-breeder / hobby exemptions and their exact thresholds. (Keeping being free does NOT imply selling is.)
- **Import/export classification:** for cross-border movement, is the species treated as **"wildlife"**
  (triggering a wildlife declaration/permit/designated port even for a captive-bred pet) or **"domesticated"**
  (exempt)? Check the specific list or definition rather than assuming.
- **Pest / invasive classification:** does the jurisdiction classify _{{SPECIES_LATIN}}_ as non-native,
  invasive, nuisance, pest, prohibited, or conditional, and does that trigger any separate rule (no-release,
  eradication, possession ban, etc.)? Note whether such a rule reaches a captive-bred pet or only wild populations.
- **If the law is silent or genuinely unclear, say so**, and name the exact agency office that could
  clarify (office name + a contact URL or phone if available).
- **Local-language terms** (species names, statute and agency names, search phrases) if the jurisdiction's
  primary language is not English.

**Rules:**
- Cite **official primary sources**. Every status must have a source URL. If you cannot find a source,
  mark the activity `Unregulated/unclear` and state what you searched.
- **Do not give legal advice** or opinions on what someone "should" do. Report what the official sources say.
- Prefer **current** law; note the date of each source and any pending or recent changes.
- For anything **unresolved**, capture the **exact agency contact** so a follow-up inquiry can be sent:
  office name, official **email address**, **web contact-form URL**, **phone**, and mailing address if
  available, plus the precise question to put to them.

**Output format:**
- **A. Summary** — 3 to 4 plain-language sentences.
- **B. Table** — Activity | Status | Why (one line) | Governing law | Source URL | Confidence.
- **C. Restrictions** — as described above.
- **D. Sources** — Title — Authority — URL (official sources first).
- **E. Open questions / what to confirm with the agency.**
- **F. Agency contacts** — for each agency involved (and any unresolved point): office name, official
  email, web contact-form URL, phone, mailing address if available, and the exact question to ask.

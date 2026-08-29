# VFN Terminal v2

Public-only market intelligence + special situations terminal.

## What changed in v2

- New denser terminal design: system sans-serif for headlines, Georgia for research prose, monospace for data/navigation.
- Search boxes on both live views.
- Source-universe display and coverage counters.
- Expanded event taxonomy: M&A, strategic review, spin-off, divestiture, activism, restructuring and filing signals.
- Special Situations table adds NEW/UPDATE signal and Next Step / Catalyst.
- Much broader automated collection:
  - Apollo — The Daily Spark
  - Axios newsletter index
  - Guardian Business / Technology / World RSS
  - Federal Reserve
  - U.S. Treasury
  - SEC press/litigation pages
  - PR Newswire general + M&A
  - FTC competition
  - DOJ Antitrust
  - UK CMA merger cases
  - European Commission merger + antitrust news
  - EDGAR screens for 8-K, 6-K, 425, S-4, DEFM14A, PREM14A, SC 13D/A, tender-offer forms, 13E-3, 10-Q and 10-K
- Three weekday refreshes: pre-market, midday, after close.
- Optional OpenAI layer for ranking, factual summaries and investor takeaways.

## Deployment

Best setup: GitHub repository -> Netlify.

1. Upload this whole folder to a GitHub repo.
2. In Netlify, deploy from that repo.
3. GitHub Actions will update `data/digest.json` and `data/special_situations.json`.
4. Each commit causes Netlify to redeploy automatically.

## GitHub secrets

Go to GitHub repo -> Settings -> Secrets and variables -> Actions.

Create:

### SEC_USER_AGENT
Use an identifiable value, e.g.
`Tae Kim taekim2029@u.northwestern.edu`

### OPENAI_API_KEY (recommended)
If set, the updater asks an LLM to:
- rank the most relevant daily items,
- summarize them without inventing unsupported details,
- write the equity/credit takeaway,
- classify special-situations events and identify the next thing to monitor.

Do not place this key in the website files.

Optional repository variable:
`OPENAI_MODEL=gpt-5.6-luna`

The low-cost model is appropriate for a recurring classification/summarization workflow. You can change it later.

## Why this architecture

The public site remains a static Netlify site. The GitHub Action is the research/data pipeline. That means:
- no public credentials,
- no browser-side scraping,
- no private editor,
- no manual redeployment after each update.

## Important source / legal behavior

The collector does not bypass authentication, subscriber-only newsletter delivery, or paywalls. It takes headlines/snippets from public pages/feeds and links back to the original source. Public pages change over time, so HTML collectors may occasionally need maintenance. RSS and official regulatory/SEC feeds are more stable and are preferred where available.

## Quality hierarchy

1. Primary filings / regulators.
2. Reputable public news / newsletter pages.
3. Company/press-wire announcements.
4. LLM classification and synthesis only after source collection.

The AI layer is instructed not to manufacture tickers, deal terms or facts missing from the collected source text. Every rendered item includes the source link so it can be verified quickly.


## v4 volume targets

The collector is now intentionally broad.

- Digest target: **55 items** in the free/no-AI fallback, or 50–60 when an AI ranking layer is later enabled.
- Special Situations target: **up to 18 material event candidates** in the free fallback, or 15–20 with an AI classification layer.
- Source/screen universe: **100+ named feeds, public pages, regulatory sources and SEC form screens**.

The website does not invent filler to reach those numbers. If fewer than 55 genuinely retrievable public items are collected on a quiet day or one or more external pages fail, it will show fewer rather than duplicate stories.

### Zero-cost configuration

For the free version, GitHub Actions needs only:

`SEC_USER_AGENT`

You can leave `OPENAI_API_KEY` unset. The updater will use deterministic ranking, event classification and rule-based investor takeaways.

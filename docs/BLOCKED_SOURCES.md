# Blocked and deferred news sources

ReadLogue’s default ingest runs on **GitHub Actions** (`reader/0.1.0` User-Agent, Azure/datacenter egress). Many publishers block, throttle, or serve empty pages to that traffic even when the same URLs work from a home or office network.

This file records sources we **cannot reliably ingest on GHA today**, why, and what was already tried. Config entries may still exist in [`config.yaml`](../config.yaml) with `enabled: false` for local runs or future retries.

**Last updated:** 2026-06-28 (session history through AU gov GHA batch)

---

## Status key

| Status | Meaning |
|--------|---------|
| **Blocked (GHA)** | Fails on every GHA attempt; may work locally |
| **Blocked (everywhere)** | Fails from dev environment too (WAF, paywall, empty discovery) |
| **Digest-only** | Feed/listing works but content is too short for full-text pipeline |
| **Deferred** | Needs new scraper/API work before worth enabling |
| **GHA OK** | Validated on GHA; disabled only to narrow test batches |

---

## International — RSS / Cloudflare

### The Batch (`the-batch`)

| | |
|---|---|
| **URL** | Discovery: [Turing proxy RSS](https://raw.githubusercontent.com/alan-turing-institute/ai-rss-feeds/refs/heads/main/feeds/the-batch.xml) → `https://www.deeplearning.ai/the-batch/issue-*` |
| **Config** | `the-batch` in [`config.yaml`](../config.yaml), `enabled: false` |
| **Status** | **Blocked (GHA)** |

**Why:** DeepLearning.ai returns **403 Forbidden** to GitHub Actions datacenter IPs. The Turing Institute proxy RSS only exposes one-line teasers, not full newsletter HTML.

**What we tried:**
1. Standard RSS → fetch full article URL (`requests`).
2. `settings.fetcher: playwright` on GHA — Playwright returned **teaser-only HTML** (~3300 words locally via `requests`, but not full issue body from GHA browser path).
3. Per-URL 403 handling so one failure does not abort the whole source (still 0 articles stored).

**Alternatives:** Manual import / RSS-metadata stubs (see README Phase 2 roadmap); residential proxy; official API if DeepLearning.ai offers one; ingest from a non-datacenter runner.

---

### Turing Institute blog (`turing-blog`)

| | |
|---|---|
| **URL** | [Turing proxy RSS](https://raw.githubusercontent.com/alan-turing-institute/ai-rss-feeds/refs/heads/main/feeds/turing-blog.xml) → `https://www.turing.ac.uk/blog/*` |
| **Config** | `turing-blog`, `enabled: false` |
| **Status** | **Blocked (everywhere)** |

**Why:** `turing.ac.uk` sits behind **Cloudflare**. All fetches get **403** with a “Just a moment…” challenge — not a User-Agent quirk (same with Chrome UA and no UA).

**What we tried:**
1. `requests` with `reader/0.1.0` and browser User-Agent.
2. `fetcher: playwright` locally and on GHA — still lands on **challenge/interstitial** pages; validation rejects stored content.
3. Added Cloudflare/challenge detection in validation (v1.4.5).

**Alternatives:** Manual import; RSS metadata-only UI; unlikely to work from GHA without proxy or publisher allowlisting.

---

### ACM TechNews (`acm-technews`)

| | |
|---|---|
| **URL** | `https://technews.acm.org/` — official feed: `https://rss.acm.org/technews/technews.xml` |
| **Config** | `acm-technews`, `enabled: false` |
| **Status** | **Digest-only** (rejected for full-text ingest) |

**Why:** ACM TechNews is a **curated digest** linking to third-party sites (Politico, Ars Technica, AP, etc.). RSS body is ~**80–90 words** — passes validation only if we store the digest, not full articles. Chasing original URLs is **patchy** (e.g. Politico 403, others OK). User decision: **do not populate DB with brief summaries only**.

**What we tried:**
1. Full-article fetch from external URLs — mixed success, GHA-dependent.
2. `use_feed_content: true` — stores ~80-word RSS digest; **disabled** after GHA QA.
3. Homepage scrape — not suitable; use RSS for discovery only.

**Alternatives:** Keep disabled; or re-enable digest mode explicitly if short summaries become acceptable; manual import for selected stories.

---

### Wiley AI Magazine

| | |
|---|---|
| **URL** | `https://onlinelibrary.wiley.com/journal/23719621` |
| **Config** | Not added |
| **Status** | **Blocked (everywhere)** — out of scope for current pipeline |

**Why:** Journal site **403** (Cloudflare). RSS `https://onlinelibrary.wiley.com/feed/23719621/most-recent` works but items are **TOC metadata only** (~8 words) — fails 50-word minimum. DOI article pages also **403**; full text is paywalled.

**What we tried:** RSS parse, sample DOI fetch, feasibility assessment (Jun 2026).

**Alternatives:** Bibliographic/metadata-only item type; institutional access/API; skip.

---

## Australian universities

### UniMelb newsroom — Engineering & IT / Education

| | |
|---|---|
| **URLs** | RSS: `https://www.unimelb.edu.au/newsroom/feed?queries_category_query=4000908` (Eng/IT), `4000907` (Education) |
| | Listing: `https://www.unimelb.edu.au/newsroom/topics?queries_category_query=4000908` (and `4000907`) |
| **Config** | `unimelb-newsroom-eng-it`, `unimelb-newsroom-education` — [`config/sources/unimelb-newsroom.yaml`](../config/sources/unimelb-newsroom.yaml), `enabled: false` |
| **Status** | **Blocked (GHA)** |

**Why:** UniMelb is behind **Cloudflare**. From GHA: topic **RSS feeds 403**; topic **listing pages 403** with `requests`. Listing/article paths need **Playwright**; article pages also **403** on `requests` from datacenter IPs.

**What we tried:**
1. RSS with topic filter (`queries_category_query`) — worked locally (~10 entries); **403 on GHA**.
2. Switched to topic **listing** scrape — listing URL also **403 on GHA** (despite working with `reader/0.1.0` from some networks).
3. `listing_fetcher: playwright` + browser context for listing discovery.
4. `fetcher: playwright` for article bodies (skip requests→403 retry round-trip).
5. Playwright worked in local GHA simulation; still disabled pending stable cadence / cost (~40 browser startups per run noted).

**Alternatives:** Self-hosted runner; local/cron ingest; re-enable when Playwright cost is acceptable.

---

### Sydney Engineering news (2026 page)

| | |
|---|---|
| **URL** | `https://www.sydney.edu.au/engineering/news-and-events/news/2026.html` |
| **Config** | Not added |
| **Status** | **Blocked (everywhere)** for this URL |

**Why:** 2026 listing uses **Coveo Atomic Search** — article results load via JavaScript. Static HTML has **zero article URLs** (only year/month nav). Site is mid-migration: older paths like `.../news/2024/11.html` have static links and articles fetch (~211 words), but **2025/2026 month pages are empty** in static HTML.

**What we tried:** Coveo detection, 2024 archive probe, month-page link extraction, sample article fetch on 2024 URLs.

**Alternatives:** Playwright + rendered search; Coveo API integration; use 2024 archive only (stale); wait for static HTML to return.

---

### Monash IT news

| | |
|---|---|
| **URL** | `https://www.monash.edu/it/news` |
| **Config** | Not added |
| **Status** | **Blocked (everywhere)** |

**Why:** Declared RSS `https://www.monash.edu/monash-mango/_web_services/news/rss?site=466676` returns **`Error in REST response`** (empty). News page returns **403** even with browser User-Agent. Playwright on listing yields ~54 words (page chrome, not articles).

**What we tried:** RSS probe, listing scrape, Playwright, browser User-Agent.

**Alternatives:** Same class as Cloudflare/datacenter blocks; manual tracking or different Monash news endpoint if one appears.

---

### CAIDE (UniMelb Centre for AI and Digital Ethics)

| | |
|---|---|
| **URL** | `https://www.unimelb.edu.au/caide` |
| **Config** | Not added |
| **Status** | **Blocked (everywhere)** — no crawlable index |

**Why:** No dedicated news RSS. Probed `/caide/news`, `/caide/media`, `/caide/feed`, `/caide/rss` — **404/403**. `/caide/events/caide-news` and `/caide/events/blog` listing pages are **empty** in HTML. Homepage features occasional single items (e.g. seed funding announcement, ~353 words when fetched) but no populated index.

**What we tried:** Path probing, listing scrape, sample article fetch.

**Alternatives:** Manual slug list; watch UniMelb newsroom (university-wide, not CAIDE-specific); sitemap crawl if index appears later.

---

### CIS UniMelb (related — not on your list but tested)

| | |
|---|---|
| **URL** | `https://cis.unimelb.edu.au/news-and-events` |
| **Status** | **Deferred** — custom feed API required |

**Why:** Page HTML is a shell; “Show more” is JS. Articles come from embedded **Matrix feed processor** on `cms.unimelb.edu.au` (not the page URL). Standard listing scrape on the public URL finds **0 links**.

**Alternatives:** Custom handler pointing at the feed API URL; Playwright with pagination.

---

### CSIRO filtered news (tested during AU gov batch)

| | |
|---|---|
| **URL** | Filtered `https://www.csiro.au/en/news/All?type={…}&cat={…}` |
| **Config** | Not added |
| **Status** | **Blocked (everywhere)** |

**Why:** Static HTML shows **0 results**; Playwright still **0 article links**. Filter appears JS/API-driven.

**What we tried:** `requests`, Playwright (90s timeout), unfiltered `/en/news/all/articles` probe.

---

## Australian government / policy

### AI.gov.au blog (`ai-gov-blog`)

| | |
|---|---|
| **URLs** | Listing: `https://www.ai.gov.au/news-and-insights/blog` — RSS: `https://www.ai.gov.au/rss.xml` (blog + events) |
| **Config** | `ai-gov-blog`, `enabled: false` |
| **Status** | **Blocked (GHA)** |

**Why:** Entire `www.ai.gov.au` **read-timeout** from GHA (60s) on both listing HTML and RSS — works locally in **&lt;0.1s**.

**What we tried:**
1. Listing scrape (`requests`, `timeout: 60`).
2. Switched to RSS + `allowed_url_prefixes` for blog-only — **RSS also times out on GHA**.
3. Playwright fallback on timeout (not reached if connection hangs).

**Alternatives:** Local ingest; AU-based runner; proxy egress.

---

### DTA AI articles (`dta-news-ai`)

| | |
|---|---|
| **URLs** | `https://www.dta.gov.au/articles`, filtered `/news?field_tags=33`, site RSS `https://www.dta.gov.au/rss.xml` |
| **Config** | `dta-news-ai`, `enabled: false` |
| **Status** | **Blocked (GHA)** |

**Why:** `www.dta.gov.au` **read-timeout** from GHA on listing pages (`/articles`, filtered `/news`). Works locally (~0.2s). Site RSS works locally but only **1 entry** (site redesign media release) — not useful for AI article discovery.

**What we tried:**
1. Filtered `/news?…field_tags=33` listing.
2. Lighter `/articles` listing URL.
3. `timeout: 60`, `requests` then Playwright on timeout — **Playwright also 60s timeout on GHA**.

**Alternatives:** Local ingest; AU runner; monitor RSS if they expand it.

---

### Industry.gov.au filtered news (`industry-gov-news`)

| | |
|---|---|
| **URL** | `https://www.industry.gov.au/news?news-entity[3988]=3988&news-entity[3333]=3333&field_news_date_value=All` |
| **Config** | `industry-gov-news`, `enabled: false` |
| **Status** | **Blocked (GHA)** |

**Why:** Listing **read-timeout** from GHA. Locally: **8 links** with `requests` on filtered URL; **0 links** with `requests` from datacenter was observed earlier, so Playwright listing was added.

**What we tried:**
1. `listing_fetcher: playwright` — GHA: `net::ERR_HTTP2_PROTOCOL_ERROR`, then **60s goto timeout**.
2. `listing_fetcher: requests` + timeout→Playwright fallback — both fail on GHA.
3. Playwright hardening: `--disable-http2`, `wait_until=commit` then `domcontentloaded` retry.
4. Plain `/news` URL (same local behavior).

**Alternatives:** Local ingest; AU runner; proxy.

---

### ATSE news (`atse-news`)

| | |
|---|---|
| **URL** | `https://www.atse.org.au/news/` (plain listing; filtered tag URL was abandoned) |
| **Config** | `atse-news` |
| **Status** | **GHA OK** — enabled in default ingest |

**Note:** Initially failed due to wrong selector (`a[href*="atse.org.au/news/"]` vs relative `/news/...` paths). Fixed to `a[href*="/news/"]`; **9 articles imported on GHA**.

---

### OAIC AI blog (`oaic-ai-blog`)

| | |
|---|---|
| **URL** | Filtered blog listing with `/s/redirect?url=…` links |
| **Config** | `oaic-ai-blog` |
| **Status** | **GHA OK** — enabled in default ingest |

Documented here for contrast — same ingest batch as blocked `.gov.au` hosts above; not blocked.

---

## Default ingest (enabled sources)

All entries in [`config.yaml`](../config.yaml) are **enabled** except the eight sources in the sections above marked **Blocked (GHA)**, **Blocked (everywhere)**, or **Digest-only**: `the-batch`, `turing-blog`, `acm-technews`, `unimelb-newsroom-eng-it`, `unimelb-newsroom-education`, `ai-gov-blog`, `dta-news-ai`, `industry-gov-news`.

---

## Sources configured but not GHA-validated

These work in **local smoke tests**; GHA behavior not confirmed in the sessions above:

| Config name | URL | Local result | GHA |
|-------------|-----|--------------|-----|
| `anu-integrated-ai-news` | `https://ai.anu.edu.au/news` | Listing ~13 links; sample ~934 words | Not tested |
| `qut-genailab` | `https://research.qut.edu.au/genailab/feed/` | RSS OK; full fetch ~537 words | Not tested |
| `rmit-news-technology` | `https://www.rmit.edu.au/news/technology` | ~9 static links; Load More is JS-only | Not tested |

---

## Cross-cutting mitigations (not yet implemented)

1. **Self-hosted GitHub Actions runner** (e.g. in Australia) for `.gov.au` and Cloudflare-heavy sites.
2. **Proxy egress** with non-datacenter IPs.
3. **Local / cron ingest** syncing to Supabase separately from GHA.
4. **RSS metadata + manual full-text import** (README Q3 2026 roadmap) for `the-batch`, `turing-blog`, and similar.
5. **Digest mode** (`use_feed_content: true`) — implemented for ACM but rejected for product reasons.

---

## Related files

- Live source toggles: [`config.yaml`](../config.yaml)
- Listing profiles: [`config/sources/`](../config/sources/)
- Ingest / fetch logic: [`src/reader/scrapers.py`](../src/reader/scrapers.py)
- Changelog notes: [`CHANGELOG.md`](../CHANGELOG.md) §1.4.8

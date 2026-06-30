# ReadLogue



## Regulatory Intelligence Pipeline

*A complete content monitoring and compliance solution, purpose‑built for the **Regulatory & Compliance Monitoring** use case.*

---

## Executive Summary

ReadLogue is a production‑ready, self‑hostable intelligence platform that automates the ingestion, curation, and archival of regulatory content from multiple public sources.

It was built to solve a specific compliance problem:

> **"How do we systematically monitor, prioritize, and preserve regulatory updates in a way that is audit‑ready and AI‑capable?"**

The solution combines automated scraping, content validation, a team‑friendly labeling dashboard, and full source archival—all on infrastructure that is cost‑effective, secure, and easy to operate.

**ReadLogue turns regulatory monitoring from a manual 'best-effort' activity into a systematic, repeatable, and audit-verifiable process.**

---

## The Problem We Solved

Compliance teams face a growing challenge:

- Regulators publish across dozens of websites, RSS feeds, and official gazettes.
- Manual monitoring is error‑prone, time‑consuming, and leaves gaps.
- When auditors ask, "How do you track regulatory changes?"—there is rarely a central, verifiable record.

ReadLogue closes that gap.

It provides a single, searchable, and auditable repository of regulatory content, enriched with your team's judgments (priority, category, relevance). Raw HTML is archived automatically, creating a provable chain of custody for every source.

---

## Solution Overview

### What It Does


| Component                  | Purpose                                                                                                   |
| -------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Automated Ingestion**    | Fetches regulatory updates from RSS feeds and official websites on a daily schedule.                      |
| **Content Validation**     | Filters out duplicates, short snippets, and low‑quality content before it reaches your team.              |
| **Labeling Dashboard**     | A secure web interface where compliance officers can review, classify, and annotate updates in real time. |
| **Audit‑Ready Archival**   | Stores raw HTML of every source in a version‑controlled repository—critical for regulatory audit trails.  |
| **Structured Data Export** | Exports labeled content in JSONL or CSV format for internal reporting or downstream analysis.             |
| **AI Foundation**          | Your labeled corpus can be used to train custom classifiers for automated prioritization (Phase 2).       |


### How It Works (High Level)

1. **Scheduler** (GitHub Actions) triggers a daily ingestion cycle.
2. **Ingestion Engine** (Python) fetches content, validates it, and extracts metadata.
3. **Storage**: Structured data is saved to Supabase (PostgreSQL). Raw HTML is archived in a separate version‑controlled repository.
4. **Dashboard**: Authorized users log in via Supabase Auth, review updates, and apply labels.
5. **Exports**: Labeled data can be exported for reporting, sharing, or AI training.

All data flows are automated, auditable, and fully containerized.

---

## Business Value

### For Compliance Teams

- **Reduce manual effort** – Automated ingestion eliminates hours of daily scanning.
- **Improve response times** – Prioritize critical updates before they become issues.
- **Strengthen audit readiness** – Every source is captured and archived with provenance.

### For Leadership

- **Visible, measurable oversight** – Dashboard shows volume, categories, and team activity.
- **AI‑ready asset** – Your labeled regulatory corpus becomes a competitive advantage.
- **Cost‑effective** – Runs on free/inexpensive infrastructure tiers.

### For IT & Security

- **Self‑hosted** – Data stays within your control (Supabase + GitHub).
- **Open source** – No vendor lock‑in; full visibility into code and data flows.
- **Standard stack** – PostgreSQL, Python, Next.js—easily supported by internal teams.
- **Data residency** - Controlled by the client; storage configurations are managed within the client's own environment (Supabase/GitHub by default), ensuring no third-party data-handling of sensitive content.

---

## Key Capabilities

### Ingestion & Validation

- Configurable Ingestion Cadence: The ingestion frequency can be adjusted via the GitHub Actions cron schedule, allowing the system to scale based on specific regulatory throughput requirements.
- Supports RSS feeds and structured listing pages.
- Configurable per source (selectors, categories, ownership, content cleanup rules).
- Article body extraction uses Trafilatura with CSS selector fallback; per-source `content_clean` rules in YAML remove site-specific junk (e.g. newsletter CTAs) before storage. Full text lives in `items.content`; list views use the 500-character `summary` only.
- Content validation filters: minimum word count, HTML residue, lexical diversity.
- Failed sources are logged for review—no silent failures.
- System includes proactive logging and alerting; failures in external source ingestion are flagged in UI and logged to GitHub Actions for immediate visibility.

### Labeling Dashboard

- Modern, responsive web interface built with Next.js + Tailwind CSS.
- Secure authentication via Supabase (email/password or SSO integration).
- Paginated article list with filtering by source, category, date, and read status.
- One‑click labeling: mark as read, set category, assign rating (Like/Dislike).
- Team visibility: annotations are stored with timestamps and user identities.
- Every label or classification applied by the team is stored with the user's identity and a UTC timestamp, creating an immutable audit trail of the team's regulatory review process.

### Archival & Provenance

- Raw HTML of every fetched article is saved to a dedicated GitHub repository.
- Each file is date‑partitioned (`YYYY‑MM‑DD/`) for easy retrieval.
- The GitHub commit history provides a verifiable audit trail.
- You can re‑extract or re‑analyze any source at any time.

### Exports & Reporting

- Export full database or filtered views in CSV or JSONL formats.
- Ready for Excel, Tableau, or custom reporting dashboards.
- JSONL format is optimized for training custom ML models (Phase 2).

---

## Technology Stack


| Layer                | Technology                | Purpose                                      |
| -------------------- | ------------------------- | -------------------------------------------- |
| **Frontend**         | Next.js + Tailwind CSS    | Team dashboard and labeling UI               |
| **Backend / API**    | Supabase (BaaS)           | Database, authentication, auto‑generated API |
| **Database**         | Supabase (PostgreSQL)     | Structured storage for articles and labels   |
| **Ingestion Engine** | Python 3.11+              | Content fetching, validation, and export     |
| **Scheduler**        | GitHub Actions            | Daily automated ingestion                    |
| **Raw HTML Archive** | GitHub Repository         | Version‑controlled, auditable source storage |
| **Hosting**          | Vercel / Cloudflare Pages | Frontend deployment                          |


All components are configured to run on generous free tiers, making this solution accessible to teams of any size.

---

## Deployment & Operations

### Environment Overview

- **Operational Cadence**: The system is engineered for flexible ingestion. While the default configuration is a daily cycle, the pipeline is designed to support high-frequency polling (e.g., hourly) for time-sensitive regulatory environments without requiring architectural changes.
- **Frontend**: Deployed to Vercel or Cloudflare Pages.
- **Database**: Supabase project (one per environment: dev/staging/prod).
- **Raw HTML Archive**:  GitHub repository (cloned during ingestion).
- **Scheduler**: GitHub Actions running on the main repository.
- **Secrets**: All credentials (Supabase keys, GitHub tokens) are stored in GitHub Secrets.

### Maintenance Effort

- **Daily**: Automated ingestion runs without human intervention.
- **Weekly**: Review ingestion logs for any source failures.
- **Monthly**: Update source selectors if regulatory websites change layout.
- **Quarterly**: Review labeling quality and export data for reporting.

### Support & Handover

- Full deployment documentation provided to the client's IT team.
- Operational runbook covers:
  - How to add/remove sources.
  - How to manage user access.
  - How to export data for reporting.
  - How to upgrade the system.
- Source code and all configuration files are delivered to the client.

---

## Roadmap (Phase 2)


| Quarter     | Capability                                                                                                                                                                                                                                          |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Q3 2026** | AI‑powered prioritization: automatically flag high‑urgency updates based on your labeling history.                                                                                                                                                  |
| **Q3 2026** | **RSS metadata + manual import:** when full article fetch is blocked (e.g. Cloudflare on GHA), ingest RSS title/link/summary as stub items; dashboard lists them with a manual import path to paste or upload full text for labeling and ML export. |
| **Q4 2026** | Slack/Teams integration: push daily digests to compliance channels.                                                                                                                                                                                 |
| **Q1 2027** | Multi‑team support: role‑based access for legal, compliance, and risk teams.                                                                                                                                                                        |
| **Q2 2027** | Regulatory calendar integration: auto‑map updates to internal compliance deadlines.                                                                                                                                                                 |


---

## About This Project

This solution was designed and built by **WizeIdea**, a systems‑integration consultancy specialising in AI‑ready data pipelines and governance automation.

We combined modern, open‑source tooling with a modular architecture to create a solution that is:

- **Cost‑effective** – low ongoing operational costs.
- **Secure** – data remains within the client's control.
- **Extensible** – ready for AI integration in Phase 2.

---

## License

Apache 2.0 License.

---

## Contact

For inquiries about deployment, customisation, or Phase 2 integration, please contact:

**WizeIdea** [https://wizeidea.com](https://wizeidea.com)

---

*ReadLogue: Compliance monitoring, automated. Audit‑ready by design.*
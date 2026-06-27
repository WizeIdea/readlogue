from __future__ import annotations

import unittest
from pathlib import Path

from reader.config import ContentCleanRules, load_listing_profile
from reader.content_clean import clean_content

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINEERING_RULES = load_listing_profile(REPO_ROOT / "config/sources/anthropic-engineering.yaml").content_clean
RESEARCH_RULES = load_listing_profile(REPO_ROOT / "config/sources/anthropic-research.yaml").content_clean
NEWS_RULES = load_listing_profile(REPO_ROOT / "config/sources/anthropic-news.yaml").content_clean
FRONTIER_RULES = load_listing_profile(REPO_ROOT / "config/sources/anthropic-frontier-red-team.yaml").content_clean
AISI_RULES = load_listing_profile(REPO_ROOT / "config/sources/aisi-blog.yaml").content_clean


class ContentCleanTests(unittest.TestCase):
    def test_engineering_strips_developer_newsletter_heading(self) -> None:
        content = "## Get the developer newsletter\n\nWe built managed agents to help teams ship faster."
        cleaned = clean_content(content, ENGINEERING_RULES)
        self.assertEqual(cleaned, "We built managed agents to help teams ship faster.")

    def test_engineering_strips_newsletter_tagline(self) -> None:
        content = (
            "Product updates, how-tos, community spotlights, and more. "
            "Delivered monthly to your inbox.\n\n"
            "Get started with Claude Managed Agents by following our docs."
        )
        cleaned = clean_content(content, ENGINEERING_RULES)
        self.assertEqual(cleaned, "Get started with Claude Managed Agents by following our docs.")

    def test_frontier_red_team_strips_newsletter_block(self) -> None:
        content = (
            "## Subscribe to the Frontier Red Team newsletter\n\n"
            "Get updates on our latest red-teaming research and findings.\n\n"
            "Claude Mythos Preview's ability to develop exploits is a step-change."
        )
        cleaned = clean_content(content, FRONTIER_RULES)
        self.assertEqual(
            cleaned,
            "Claude Mythos Preview's ability to develop exploits is a step-change.",
        )

    def test_research_strips_frontier_red_team_heading(self) -> None:
        content = "## Subscribe to the Frontier Red Team newsletter\n\nPhase two of Project Fetch."
        cleaned = clean_content(content, RESEARCH_RULES)
        self.assertEqual(cleaned, "Phase two of Project Fetch.")

    def test_research_strips_anthropic_science_heading(self) -> None:
        content = "## Subscribe to Anthropic Science\n\nAgents in biology need careful evaluation."
        cleaned = clean_content(content, RESEARCH_RULES)
        self.assertEqual(cleaned, "Agents in biology need careful evaluation.")

    def test_news_strips_heading_without_hash_prefix(self) -> None:
        content = "Subscribe to the Frontier Red Team newsletter\n\nMITRE ATT&CK coverage for AI threats."
        cleaned = clean_content(content, NEWS_RULES)
        self.assertEqual(cleaned, "MITRE ATT&CK coverage for AI threats.")

    def test_news_strips_heading_with_double_hash(self) -> None:
        content = "## Subscribe to the Frontier Red Team newsletter\n\nMITRE ATT&CK coverage for AI threats."
        cleaned = clean_content(content, NEWS_RULES)
        self.assertEqual(cleaned, "MITRE ATT&CK coverage for AI threats.")

    def test_strips_leading_blank_lines_before_junk(self) -> None:
        content = "\n\n## Get the developer newsletter\n\nArticle body."
        cleaned = clean_content(content, ENGINEERING_RULES)
        self.assertEqual(cleaned, "Article body.")

    def test_no_op_when_rules_empty(self) -> None:
        content = "## Get the developer newsletter\n\nArticle body."
        cleaned = clean_content(content, ContentCleanRules())
        self.assertEqual(cleaned, content)

    def test_no_op_when_rules_none(self) -> None:
        content = "## Get the developer newsletter\n\nArticle body."
        cleaned = clean_content(content, None)
        self.assertEqual(cleaned, content)

    def test_strip_prefix_literals(self) -> None:
        rules = ContentCleanRules(strip_prefix_literals=("JUNK\n\n",))
        content = "JUNK\n\nReal article text."
        cleaned = clean_content(content, rules)
        self.assertEqual(cleaned, "Real article text.")

    def test_aisi_strips_rename_disclaimer(self) -> None:
        content = (
            "*Note to readers: we changed our name to the AI Security Institute on "
            "14 February 2025. Read more** here.*\n\n"
            "A key part of our work at the AI Safety Institute involves evaluating advanced AI systems."
        )
        cleaned = clean_content(content, AISI_RULES)
        self.assertEqual(
            cleaned,
            "A key part of our work at the AI Safety Institute involves evaluating advanced AI systems.",
        )

    def test_body_preserved_when_no_junk_prefix(self) -> None:
        content = "Real article text with no newsletter heading."
        self.assertEqual(clean_content(content, ENGINEERING_RULES), content)


if __name__ == "__main__":
    unittest.main()

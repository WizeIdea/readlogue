from __future__ import annotations

import unittest
from pathlib import Path

from reader.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config.yaml"

# Keep in sync with docs/BLOCKED_SOURCES.md
BLOCKED_SOURCES = frozenset(
    {
        "the-batch",
        "turing-blog",
        "acm-technews",
        "unimelb-newsroom-eng-it",
        "unimelb-newsroom-education",
        "ai-gov-blog",
        "dta-news-ai",
        "industry-gov-news",
    }
)


class ConfigVocabularyTests(unittest.TestCase):
    def test_config_loads_curation_vocabularies(self) -> None:
        config = load_config(CONFIG_PATH)
        self.assertIn("research", config.article_types)
        self.assertIn("LLMs", config.article_domains)

    def test_only_blocked_sources_are_disabled(self) -> None:
        config = load_config(CONFIG_PATH)
        disabled = {source.name for source in config.sources if not source.enabled}
        self.assertEqual(disabled, set(BLOCKED_SOURCES))

from __future__ import annotations

import unittest
from pathlib import Path

from reader.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config.yaml"


class ConfigVocabularyTests(unittest.TestCase):
    def test_config_loads_curation_vocabularies(self) -> None:
        config = load_config(CONFIG_PATH)
        self.assertIn("research", config.article_types)
        self.assertIn("LLMs", config.article_domains)

    def test_gha_batch_enables_only_four_vendor_sources(self) -> None:
        config = load_config(CONFIG_PATH)
        enabled = {source.name for source in config.sources if source.enabled}
        self.assertEqual(
            enabled,
            {
                "thinking-machines-blog",
                "google-developers-blog-ai",
                "meta-ai-blog",
                "groq-blog",
            },
        )

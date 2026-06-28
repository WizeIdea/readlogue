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

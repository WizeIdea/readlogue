from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

from reader.config import load_categories

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config.yaml"
CATEGORIES_TS = REPO_ROOT / "apps/web/src/lib/categories.ts"


def _parse_categories_ts(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"export const CATEGORIES = \[(.*?)\] as const;", text, re.S)
    if not match:
        raise AssertionError(f"Could not parse CATEGORIES from {path}")
    block = match.group(1)
    return re.findall(r'"((?:\\.|[^"\\])*)"', block)


class CategoriesSyncTests(unittest.TestCase):
    def test_categories_ts_matches_config_yaml(self) -> None:
        expected = load_categories(CONFIG_PATH)
        actual = _parse_categories_ts(CATEGORIES_TS)
        self.assertEqual(actual, expected)

    def test_config_yaml_requires_categories(self) -> None:
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        self.assertIn("categories", raw)
        self.assertIsInstance(raw["categories"], list)
        self.assertGreater(len(raw["categories"]), 0)

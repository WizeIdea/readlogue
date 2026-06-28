from __future__ import annotations

import re
import unittest
from pathlib import Path

from reader.config import (
    load_article_domains,
    load_article_types,
    load_categories,
    load_source_names,
    load_web_sources,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config.yaml"
CATEGORIES_TS = REPO_ROOT / "apps/web/src/lib/categories.ts"
PICKLISTS_TS = REPO_ROOT / "apps/web/src/lib/curation-picklists.ts"
SOURCES_TS = REPO_ROOT / "apps/web/src/lib/sources.ts"


def _parse_ts_string_array(path: Path, const_name: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    pattern = rf"export const {const_name} = \[(.*?)\] as const;"
    match = re.search(pattern, text, re.S)
    if not match:
        raise AssertionError(f"Could not parse {const_name} from {path}")
    return re.findall(r'"((?:\\.|[^"\\])*)"', match.group(1))


class VocabSyncTests(unittest.TestCase):
    def test_categories_ts_matches_config_yaml(self) -> None:
        expected = load_categories(CONFIG_PATH)
        actual = _parse_ts_string_array(CATEGORIES_TS, "CATEGORIES")
        self.assertEqual(actual, expected)

    def test_curation_picklists_ts_matches_config_yaml(self) -> None:
        expected_types = load_article_types(CONFIG_PATH)
        expected_domains = load_article_domains(CONFIG_PATH)
        actual_types = _parse_ts_string_array(PICKLISTS_TS, "ARTICLE_TYPES")
        actual_domains = _parse_ts_string_array(PICKLISTS_TS, "ARTICLE_DOMAINS")
        self.assertEqual(actual_types, expected_types)
        self.assertEqual(actual_domains, expected_domains)

    def test_sources_ts_matches_config_yaml(self) -> None:
        expected = load_source_names(CONFIG_PATH)
        actual = _parse_ts_string_array(SOURCES_TS, "SOURCES")
        self.assertEqual(actual, expected)

    def test_source_display_names_match_config_yaml(self) -> None:
        expected = {
            source.name: source.display_name for source in load_web_sources(CONFIG_PATH)
        }
        text = SOURCES_TS.read_text(encoding="utf-8")
        match = re.search(
            r"export const SOURCE_DISPLAY_NAMES: Record<SourceName, string> = \{(.*?)\};",
            text,
            re.S,
        )
        self.assertIsNotNone(match, "SOURCE_DISPLAY_NAMES block missing")
        block = match.group(1)
        actual = dict(re.findall(r'"((?:\\.|[^"\\])*)":\s*"((?:\\.|[^"\\])*)"', block))
        self.assertEqual(actual, expected)

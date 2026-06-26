from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from reader.config_edit import append_ignored_url


class ConfigEditTests(unittest.TestCase):
    def test_append_ignored_url_substring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text("ignored_url_substrings: []\n", encoding="utf-8")
            field, value = append_ignored_url(
                config_path,
                "https://deepmind.google/blog/introducing-google-antigravity/",
            )
            self.assertEqual(field, "ignored_url_substrings")
            self.assertEqual(value, "introducing-google-antigravity")
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            self.assertIn("introducing-google-antigravity", raw["ignored_url_substrings"])

    def test_append_ignored_url_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config_path.write_text("ignored_urls: []\n", encoding="utf-8")
            url = "https://example.com/article"
            field, value = append_ignored_url(config_path, url, use_substring=False)
            self.assertEqual(field, "ignored_urls")
            self.assertEqual(value, url)

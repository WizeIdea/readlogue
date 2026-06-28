from __future__ import annotations

import unittest

from reader.curation import normalize_curation, parse_curation_json, serialize_curation


class CurationTests(unittest.TestCase):
    def test_empty_curation_round_trip(self) -> None:
        self.assertEqual(parse_curation_json("{}"), {})
        self.assertEqual(serialize_curation({}), "{}")

    def test_normalize_tags_and_scores(self) -> None:
        raw = {
            "article_types": ["research", " governance ", ""],
            "article_domains": ["LLMs", "policy"],
            "technical_depth": 4,
            "business_relevance": 0,
            "governance_relevance": "5",
        }
        normalized = normalize_curation(raw)
        self.assertEqual(normalized["article_types"], ["research", "governance"])
        self.assertEqual(normalized["article_domains"], ["LLMs", "policy"])
        self.assertEqual(normalized["technical_depth"], 4)
        self.assertNotIn("business_relevance", normalized)
        self.assertEqual(normalized["governance_relevance"], 5)

    def test_normalize_empty_after_stripping(self) -> None:
        self.assertEqual(normalize_curation({"technical_depth": 9}), {})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from reader.validation import ContentQuality, validate_content


def _diverse_text(n: int) -> str:
    """Produce *n* words with enough lexical diversity to pass the 20 % check."""
    # Use every word from the standard Lorem Ipsum, cycling if needed.
    lorem = (
        "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
        "tempor incididunt ut labore et dolore magna aliqua ut enim ad minim veniam "
        "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo "
        "consequat duis aute irure dolor in reprehenderit in voluptate velit esse "
        "cillum dolore eu fugiat nulla pariatur excepteur sint occaecat cupidatat "
        "non proident sunt culpa qui officia deserunt mollit anim id est laborum"
    )
    pool = lorem.split()
    # cycle: pick words so that when n=50 we have at least ~50% unique
    return " ".join(pool[i % len(pool)] for i in range(n))


class ValidateContentTests(unittest.TestCase):
    def test_valid_content_passes(self) -> None:
        text = _diverse_text(100)
        quality = validate_content("Some Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)
        self.assertEqual(quality.word_count, 100)

    def test_empty_content_fails(self) -> None:
        quality = validate_content("Title", "", "https://example.com/a", "test-source")
        self.assertFalse(quality.is_valid)
        self.assertIn("too short", (quality.reason or "").lower())

    def test_short_content_fails(self) -> None:
        text = _diverse_text(10)
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertFalse(quality.is_valid)
        self.assertIn("too short", (quality.reason or "").lower())

    def test_content_just_above_threshold_passes(self) -> None:
        text = _diverse_text(50)
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)

    def test_content_with_html_residue_fails(self) -> None:
        text = _diverse_text(60) + " <div class=\"content\">more text</div>"
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertFalse(quality.is_valid)
        self.assertTrue(quality.html_residue)
        self.assertIn("HTML", (quality.reason or ""))

    def test_content_with_self_closing_tag_residue_fails(self) -> None:
        text = _diverse_text(60) + " <br/> more"
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertFalse(quality.is_valid)
        self.assertTrue(quality.html_residue)

    def test_low_diversity_content_fails(self) -> None:
        # Only uses 2 unique words -> diversity ~ 3.3%
        text = " ".join(["hello"] * 30 + ["world"] * 30)
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertFalse(quality.is_valid)
        self.assertTrue(quality.low_diversity)
        self.assertIn("diversity", (quality.reason or "").lower())

    def test_high_diversity_passes(self) -> None:
        # 50 unique words out of 60 -> diversity ~ 83%
        words = [f"word{i}" for i in range(50)] + ["the"] * 10
        text = " ".join(words)
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)
        self.assertFalse(quality.low_diversity)

    def test_custom_min_word_count(self) -> None:
        text = _diverse_text(100)
        quality = validate_content("Title", text, "https://example.com/a", "test-source", min_word_count=200)
        self.assertFalse(quality.is_valid)
        self.assertIn("too short", (quality.reason or "").lower())

    def test_whitespace_only_content_fails(self) -> None:
        quality = validate_content("Title", "   \n\n   ", "https://example.com/a", "test-source")
        self.assertFalse(quality.is_valid)
        self.assertIn("too short", (quality.reason or "").lower())

    def test_content_near_boundary_still_passes(self) -> None:
        # 51 words, should pass the default threshold of 50
        text = _diverse_text(51)
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)

    def test_inline_code_pseudo_tags_pass(self) -> None:
        text = _diverse_text(60) + " They use trainable control tokens (`<think_i>`) in the model."
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)

    def test_angle_bracket_urls_pass(self) -> None:
        text = _diverse_text(60) + " See <https://example.com> for details."
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)

    def test_pascal_case_notation_passes(self) -> None:
        text = _diverse_text(60) + " The <Parallel> operator coordinates independent subtasks."
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)

    def test_real_html_residue_still_fails(self) -> None:
        text = _diverse_text(60) + ' <div class="content">more text</div>'
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertFalse(quality.is_valid)
        self.assertTrue(quality.html_residue)

    def test_bash_pseudo_tags_pass(self) -> None:
        text = _diverse_text(60) + " [Tool Use] <bash - pwd> and <bash - git log --oneline -20>"
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)

    def test_document_chunk_pseudo_tags_pass(self) -> None:
        text = _diverse_text(60) + " Split into <document> sections with <chunk> boundaries </chunk> </document>"
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)

    def test_mask_and_redacted_thinking_pass(self) -> None:
        text = _diverse_text(60) + " Uses <mask> tokens and </think> markers in prose."
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)

    def test_fenced_code_block_tags_pass(self) -> None:
        text = _diverse_text(60) + "\n```\n<bash>\necho hello\n</bash>\n```\n"
        quality = validate_content("Title", text, "https://example.com/a", "test-source")
        self.assertTrue(quality.is_valid)

    def test_bot_challenge_page_fails(self) -> None:
        text = (
            "# www.turing.ac.uk\n\n"
            "## Performing security verification\n\n"
            "This website uses a security service to protect against malicious bots. "
            "This page is displayed while the website verifies you are not a bot.\n\n"
            "This website uses a security service to protect against malicious bots. "
            "This page is displayed while the website verifies you are not a bot."
        )
        quality = validate_content("www.turing.ac.uk", text, "https://www.turing.ac.uk/blog/x", "turing-blog")
        self.assertFalse(quality.is_valid)
        self.assertIn("bot-protection", (quality.reason or "").lower())


if __name__ == "__main__":
    unittest.main()
from __future__ import annotations

import re
from dataclasses import dataclass

# Default threshold
_MIN_WORD_COUNT = 50

# Roughly 200 of the most common English stop words, used as a simple heuristic
# to distinguish real text from boilerplate / garbage.
_ENGLISH_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "about", "above", "across", "after", "again", "all", "almost",
        "along", "also", "am", "among", "an", "and", "another", "any",
        "are", "as", "at", "be", "because", "been", "before", "being",
        "below", "between", "both", "but", "by", "came", "can", "did",
        "do", "does", "done", "down", "each", "few", "find", "for",
        "from", "further", "get", "give", "go", "had", "has", "have",
        "having", "he", "hence", "her", "here", "hereafter", "hereby",
        "herein", "hereupon", "hers", "herself", "him", "himself", "his",
        "how", "however", "i", "if", "in", "into", "is", "it", "its",
        "itself", "just", "like", "made", "make", "many", "may", "me",
        "meanwhile", "might", "more", "most", "much", "must", "my",
        "myself", "namely", "neither", "never", "nevertheless", "next",
        "no", "nobody", "none", "noone", "nor", "not", "nothing", "now",
        "nowhere", "of", "off", "often", "on", "once", "one", "only",
        "onto", "or", "other", "others", "our", "ours", "ourselves", "out",
        "over", "own", "per", "perhaps", "rather", "really", "s", "said",
        "same", "she", "should", "show", "side", "since", "so", "some",
        "somehow", "someone", "something", "sometime", "sometimes",
        "somewhere", "still", "such", "t", "take", "than", "that", "the",
        "their", "them", "themselves", "then", "thence", "there",
        "thereafter", "thereby", "therefore", "therein", "thereupon",
        "these", "they", "this", "those", "though", "through", "throughout",
        "thru", "thus", "to", "together", "too", "toward", "towards",
        "under", "until", "up", "upon", "us", "very", "was", "we", "were",
        "what", "whatever", "when", "whence", "whenever", "where",
        "whereafter", "whereas", "whereby", "wherein", "whereupon",
        "wherever", "whether", "which", "while", "whither", "who",
        "whoever", "whole", "whom", "whose", "why", "will", "with",
        "within", "without", "would", "yet", "you", "your", "yours",
        "yourself", "yourselves",
    }
)


@dataclass(frozen=True)
class ContentQuality:
    is_valid: bool
    reason: str | None = None
    word_count: int = 0
    html_residue: bool = False
    low_diversity: bool = False


def validate_content(
    title: str,
    content: str,
    url: str,
    source_name: str,
    *,
    min_word_count: int = _MIN_WORD_COUNT,
) -> ContentQuality:
    """Run all content-quality checks and return a summary.

    Checks performed:
    1. Minimum word count (configurable, default 50).
    2. HTML / markup residue (unescaped tags in the extracted text).
    3. Lexical diversity (ratio of unique words to total words below 20 %
       suggests repetitive boilerplate or garbage).
    """
    words = content.split()
    word_count = len(words)

    # --- 1. Minimum word count -------------------------------------------------
    if word_count < min_word_count:
        return ContentQuality(
            is_valid=False,
            reason=(
                f"content too short: {word_count} words "
                f"(minimum {min_word_count})"
            ),
            word_count=word_count,
        )

    # --- 2. HTML / markup residue --------------------------------------------
    html_residue = bool(re.search(r"<[a-zA-Z/][^>]*>", content))
    if html_residue:
        return ContentQuality(
            is_valid=False,
            reason="content contains HTML markup residue (unescaped tags)",
            word_count=word_count,
            html_residue=True,
        )

    # --- 3. Low lexical diversity (garbage / repetitive text) -----------------
    unique_words = len({w.lower() for w in words})
    diversity_ratio = unique_words / word_count if word_count > 0 else 0.0
    low_diversity = diversity_ratio < 0.20
    if low_diversity:
        return ContentQuality(
            is_valid=False,
            reason=(
                f"content has low lexical diversity "
                f"({unique_words} unique / {word_count} total = {diversity_ratio:.1%}), "
                f"likely boilerplate or garbage"
            ),
            word_count=word_count,
            low_diversity=True,
        )

    return ContentQuality(is_valid=True, word_count=word_count)
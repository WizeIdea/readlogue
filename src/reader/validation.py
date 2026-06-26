from __future__ import annotations

import re
from dataclasses import dataclass

# Default threshold
_MIN_WORD_COUNT = 50

# Common HTML5 tag names — only these count as markup residue when unescaped in Markdown.
_KNOWN_HTML_TAGS: frozenset[str] = frozenset(
    {
        "a", "abbr", "address", "area", "article", "aside", "audio", "b", "base",
        "bdi", "bdo", "blockquote", "body", "br", "button", "canvas", "caption",
        "cite", "code", "col", "colgroup", "data", "datalist", "dd", "del", "details",
        "dfn", "dialog", "div", "dl", "dt", "em", "embed", "fieldset", "figcaption",
        "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "head",
        "header", "hr", "html", "i", "iframe", "img", "input", "ins", "kbd", "label",
        "legend", "li", "link", "main", "map", "mark", "menu", "meta", "meter", "nav",
        "noscript", "object", "ol", "optgroup", "option", "output", "p", "param",
        "picture", "pre", "progress", "q", "rp", "rt", "ruby", "s", "samp", "script",
        "section", "select", "small", "source", "span", "strong", "style", "sub",
        "summary", "sup", "table", "tbody", "td", "template", "textarea", "tfoot",
        "th", "thead", "time", "title", "tr", "track", "u", "ul", "var", "video",
        "wbr",
    }
)

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
    html_residue = _has_html_residue(content)
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


def _has_html_residue(content: str) -> bool:
    """Detect unescaped HTML tags while ignoring common false positives."""
    sanitized = re.sub(r"```[\s\S]*?```", "", content)
    sanitized = re.sub(r"`[^`]*`", "", sanitized)
    sanitized = re.sub(r"<https?://[^>]+>", "", sanitized)

    for match in re.finditer(r"</?([a-zA-Z][a-zA-Z0-9]*)[^>]*>", sanitized):
        if match.group(1).lower() in _KNOWN_HTML_TAGS:
            return True
    return False
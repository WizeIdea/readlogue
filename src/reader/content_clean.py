from __future__ import annotations

import re

from reader.config import ContentCleanRules


def clean_content(content: str, rules: ContentCleanRules | None) -> str:
    """Apply per-source cleanup rules after main-text extraction."""
    if not content or rules is None or rules.is_empty():
        return content

    result = content
    for literal in rules.strip_prefix_literals:
        if result.startswith(literal):
            result = result[len(literal) :].lstrip("\n")

    if rules.strip_leading_lines_matching:
        patterns = [re.compile(pattern) for pattern in rules.strip_leading_lines_matching]
        while True:
            lines = result.splitlines()
            while lines and not lines[0].strip():
                lines.pop(0)
            if not lines:
                result = ""
                break
            first_line = lines[0].strip()
            if any(pattern.match(first_line) for pattern in patterns):
                result = "\n".join(lines[1:]).lstrip("\n")
                continue
            break

    return result.strip()

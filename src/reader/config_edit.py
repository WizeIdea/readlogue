from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml


def _url_path_segment(url: str) -> str:
    path = urlsplit(url.strip()).path.rstrip("/")
    if not path:
        return url.strip()
    return path.split("/")[-1] or path


def append_ignored_url(
    config_path: str | Path,
    article_url: str,
    *,
    use_substring: bool | None = None,
) -> tuple[str, str]:
    """Append *article_url* to the config ignore list. Returns (field_name, value_added)."""
    path = Path(config_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if use_substring is None:
        use_substring = True

    if use_substring:
        field = "ignored_url_substrings"
        value = _url_path_segment(article_url)
    else:
        field = "ignored_urls"
        value = article_url.strip()

    existing = [str(entry) for entry in raw.get(field, [])]
    if value not in existing:
        existing.append(value)
    raw[field] = existing
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return field, value

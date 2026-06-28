#!/usr/bin/env python3
"""Backward-compatible entry point — use scripts/sync_web_vocab.py."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sync_web_vocab import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

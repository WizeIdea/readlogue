from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _run_git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )


def commit_config_files(repo_root: str | Path, config_paths: list[Path], message: str) -> bool:
    """Commit config changes when READLOGUE_GITHUB_TOKEN or git credentials are available."""
    root = Path(repo_root)
    token = os.environ.get("READLOGUE_GITHUB_TOKEN", "").strip()
    if not token:
        logger.info("READLOGUE_GITHUB_TOKEN not set; skipping git push for config files")
        return False

    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = env.get("GIT_AUTHOR_NAME", "readlogue-bot")
    env["GIT_AUTHOR_EMAIL"] = env.get("GIT_AUTHOR_EMAIL", "bot@readlogue.local")

    try:
        _run_git(root, "pull", "--rebase", "origin", "main")
        for config_path in config_paths:
            relative = config_path if config_path.is_absolute() else config_path
            if not relative.is_absolute():
                relative = root / relative
            _run_git(root, "add", str(relative.relative_to(root)))
        _run_git(root, "commit", "-m", message)
        _run_git(root, "push", "origin", "HEAD:main")
    except subprocess.CalledProcessError as exc:
        logger.warning("Config git sync failed: %s", exc.stderr or exc.stdout)
        return False
    return True

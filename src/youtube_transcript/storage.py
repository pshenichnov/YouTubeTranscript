"""Filesystem persistence: write formatted transcripts to disk.

Layout produced by :func:`save_transcript`::

    <output_dir>/<video_id>/<video_id>.<lang>.txt

The output folder defaults to ``Scripts``. Inside it, a per-video subfolder is
named with the canonical video ID. One file is written per transcript language.
Sanitization (:func:`sanitize_title`) and folder-name construction
(:func:`build_folder_name`) are pure functions; the only side effect in this
module is the file write.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = "Scripts"

# Characters disallowed in Windows path components, plus ASCII control chars.
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")

# Cap folder-name length so long titles stay within path limits.
MAX_TITLE_LEN = 80


def sanitize_title(title: str) -> str:
    """Reduce a title to a safe single path component.

    Removes illegal characters, collapses whitespace to single spaces, trims, and
    caps length. May return ``""`` when nothing usable remains — callers fall
    back to the video ID in that case.
    """
    cleaned = _ILLEGAL.sub("", title)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    cleaned = cleaned[:MAX_TITLE_LEN].strip()
    # Windows forbids a trailing dot or space on a path component.
    return cleaned.rstrip(". ")


def build_folder_name(
    video_id: str,
    title: str | None = None,
    on: date | None = None,
) -> str:
    """Build the per-video subfolder name: ``<video_id>``.

    ``title`` and ``on`` are accepted for backward-compatible callers but no
    longer affect folder naming.
    """
    return video_id


def save_transcript(
    text: str,
    *,
    video_id: str,
    language: str,
    title: str | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    on: date | None = None,
) -> Path:
    """Write one language's ``text`` into the per-video subfolder.

    The file is ``<output_dir>/<video_id>/<video_id>.<language>.txt``. Folders
    are created if missing (idempotent); re-running for the same video and
    language overwrites the file.

    Returns the path of the written file.
    """
    dest_dir = Path(output_dir) / build_folder_name(video_id, title, on)
    dest_dir.mkdir(parents=True, exist_ok=True)

    path = dest_dir / f"{video_id}.{language}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def save_thumbnail(
    content: bytes,
    *,
    video_id: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Write the video's thumbnail into the per-video subfolder."""
    dest_dir = Path(output_dir) / build_folder_name(video_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    path = dest_dir / f"{video_id}.jpg"
    path.write_bytes(content)
    return path


def save_metadata(
    metadata: dict[str, Any],
    *,
    video_id: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Write the video's extraction metadata into the per-video subfolder."""
    dest_dir = Path(output_dir) / build_folder_name(video_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    path = dest_dir / f"{video_id}.metadata.json"
    path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path

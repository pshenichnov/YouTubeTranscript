"""Normalize user input down to a canonical YouTube video ID.

Pure, network-free, and the most heavily unit-tested layer.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from .models import InvalidVideoInput

# YouTube IDs are exactly 11 characters from this alphabet.
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Path-based forms map the first path segment (after a known prefix) to the ID.
_PATH_PREFIXES = ("embed", "shorts", "v", "live")


def extract_video_id(value: str) -> str:
    """Return the 11-char video ID for a bare ID or any common YouTube URL.

    Raises:
        InvalidVideoInput: the input cannot be reduced to a valid ID.
    """
    if value is None:
        raise InvalidVideoInput("expected a video ID or URL, got None")

    candidate = value.strip()
    if not candidate:
        raise InvalidVideoInput("expected a video ID or URL, got an empty string")

    # Already a bare ID.
    if _ID_RE.match(candidate):
        return candidate

    found = _id_from_url(candidate)
    if found is not None:
        return found

    raise InvalidVideoInput(f"could not extract a video ID from {value!r}")


def _id_from_url(candidate: str) -> str | None:
    # Tolerate URLs pasted without a scheme (e.g. "youtu.be/abc").
    to_parse = candidate if "://" in candidate else f"https://{candidate}"
    parsed = urlparse(to_parse)
    host = parsed.netloc.lower()

    if "youtube.com" in host:
        # watch?v=<id>
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id and _ID_RE.match(query_id):
            return query_id
        # /embed/<id>, /shorts/<id>, /v/<id>, /live/<id>
        return _id_from_path(parsed.path)

    if "youtu.be" in host:
        return _id_from_path(parsed.path)

    return None


def _id_from_path(path: str) -> str | None:
    parts = [p for p in path.split("/") if p]
    if not parts:
        return None
    # youtu.be/<id> — ID is the first segment.
    if _ID_RE.match(parts[0]):
        return parts[0]
    # youtube.com/<prefix>/<id>
    if len(parts) >= 2 and parts[0] in _PATH_PREFIXES and _ID_RE.match(parts[1]):
        return parts[1]
    return None

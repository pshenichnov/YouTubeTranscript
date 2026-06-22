"""Pure functions turning fetched segments into output text.

No network, no third-party imports — just data in, string out.
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import TranscriptSegment


def to_plain_text(segments: Iterable[TranscriptSegment]) -> str:
    """Join segment text into a single space-separated block.

    Newlines inside a segment are collapsed to spaces so the result is one
    continuous run of text.
    """
    return " ".join(seg.text.replace("\n", " ").strip() for seg in segments).strip()


def to_timestamped(segments: Iterable[TranscriptSegment]) -> str:
    """Render one ``[mm:ss] text`` line per segment."""
    return "\n".join(
        f"[{_format_timestamp(seg.start)}] {seg.text.replace(chr(10), ' ').strip()}"
        for seg in segments
    )


def _format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

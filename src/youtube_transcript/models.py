"""Pure domain types and errors shared across layers.

Nothing here touches the network or the third-party API, so every other
module can depend on it freely without pulling in those concerns.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptSegment:
    """One timed snippet of a transcript."""

    text: str
    start: float  # seconds from the start of the video
    duration: float  # seconds the snippet is shown


class TranscriptError(Exception):
    """Base class for every error this package raises deliberately."""


class InvalidVideoInput(TranscriptError):
    """The given string is neither a valid video ID nor a parseable URL."""


class TranscriptUnavailable(TranscriptError):
    """No transcript could be retrieved (disabled, missing, private, etc.)."""

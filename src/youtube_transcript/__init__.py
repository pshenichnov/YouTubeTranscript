"""Extract text transcripts from YouTube videos by video ID or URL."""

from __future__ import annotations

from .fetching import fetch_all_transcripts, fetch_transcript, fetch_video_title
from .formatting import to_plain_text, to_timestamped
from .models import (
    InvalidVideoInput,
    TranscriptError,
    TranscriptSegment,
    TranscriptUnavailable,
)
from .parsing import extract_video_id
from .service import ExtractedTranscript, TranscriptExtractionResult, extract_transcripts
from .storage import build_folder_name, sanitize_title, save_transcript

__all__ = [
    "extract_video_id",
    "extract_transcripts",
    "fetch_transcript",
    "fetch_all_transcripts",
    "fetch_video_title",
    "to_plain_text",
    "to_timestamped",
    "build_folder_name",
    "sanitize_title",
    "save_transcript",
    "ExtractedTranscript",
    "TranscriptExtractionResult",
    "TranscriptSegment",
    "TranscriptError",
    "InvalidVideoInput",
    "TranscriptUnavailable",
]

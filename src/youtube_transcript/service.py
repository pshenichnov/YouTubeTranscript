"""Reusable transcript extraction workflow shared by CLI and API callers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .fetching import fetch_all_transcripts, fetch_video_title
from .formatting import to_plain_text, to_timestamped
from .models import TranscriptSegment
from .parsing import extract_video_id
from .storage import DEFAULT_OUTPUT_DIR, save_transcript


@dataclass(frozen=True)
class ExtractedTranscript:
    """Formatted transcript data for one language."""

    language: str
    segments: list[TranscriptSegment]
    text: str
    saved_path: Path | None = None


@dataclass(frozen=True)
class TranscriptExtractionResult:
    """Complete extraction result for a single video."""

    video_id: str
    title: str | None
    transcripts: list[ExtractedTranscript]


def extract_transcripts(
    video: str,
    *,
    languages: tuple[str, ...] | None = None,
    timestamps: bool = False,
    save_to_files: bool = True,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> TranscriptExtractionResult:
    """Fetch, format, and optionally save transcripts for ``video``.

    ``video`` may be a bare YouTube video ID or a supported YouTube URL. Domain
    errors from parsing/fetching and filesystem errors from saving are allowed to
    propagate so the caller can present them in a CLI- or API-specific shape.
    """
    video_id = extract_video_id(video)
    raw_transcripts = fetch_all_transcripts(video_id, languages=languages)
    title = fetch_video_title(video_id)
    format_segments = to_timestamped if timestamps else to_plain_text

    transcripts: list[ExtractedTranscript] = []
    for language, segments in raw_transcripts.items():
        text = format_segments(segments)
        saved_path = (
            save_transcript(
                text,
                video_id=video_id,
                language=language,
                title=title,
                output_dir=output_dir,
            )
            if save_to_files
            else None
        )
        transcripts.append(
            ExtractedTranscript(
                language=language,
                segments=segments,
                text=text,
                saved_path=saved_path,
            )
        )

    return TranscriptExtractionResult(
        video_id=video_id,
        title=title,
        transcripts=transcripts,
    )

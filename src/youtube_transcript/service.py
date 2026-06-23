"""Reusable transcript extraction workflow shared by CLI and API callers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .fetching import fetch_all_transcripts, fetch_video_thumbnail, fetch_video_title
from .formatting import to_plain_text, to_timestamped
from .models import TranscriptSegment
from .parsing import extract_video_id
from .storage import DEFAULT_OUTPUT_DIR, save_metadata, save_thumbnail, save_transcript


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
    metadata_path: Path | None = None
    thumbnail_path: Path | None = None


def extract_transcripts(
    video: str,
    *,
    languages: tuple[str, ...] | None = None,
    timestamps: bool = False,
    save_to_files: bool = True,
    save_thumbnail_file: bool = False,
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

    thumbnail_path = None
    if save_to_files and save_thumbnail_file:
        thumbnail_path = save_thumbnail(
            fetch_video_thumbnail(video_id),
            video_id=video_id,
            output_dir=output_dir,
        )

    transcripts: list[ExtractedTranscript] = []
    for language, segments in raw_transcripts.items():
        text = format_segments(segments)
        saved_path = None
        if save_to_files:
            saved_path = save_transcript(
                text,
                video_id=video_id,
                language=language,
                title=title,
                output_dir=output_dir,
            )
        transcripts.append(
            ExtractedTranscript(
                language=language,
                segments=segments,
                text=text,
                saved_path=saved_path,
            )
        )

    metadata_path = None
    if save_to_files:
        metadata_path = save_metadata(
            _build_metadata(
                video_id=video_id,
                title=title,
                raw_transcripts=raw_transcripts,
            ),
            video_id=video_id,
            output_dir=output_dir,
        )

    return TranscriptExtractionResult(
        video_id=video_id,
        title=title,
        transcripts=transcripts,
        metadata_path=metadata_path,
        thumbnail_path=thumbnail_path,
    )


def _build_metadata(
    *,
    video_id: str,
    title: str | None,
    raw_transcripts: dict[str, list[TranscriptSegment]],
) -> dict[str, object]:
    duration_seconds = _duration_seconds(
        [segment for segments in raw_transcripts.values() for segment in segments]
    )
    return {
        "videoId": video_id,
        "videoTitle": title,
        "videoUrl": f"https://www.youtube.com/watch?v={video_id}",
        "videoLengthSeconds": duration_seconds,
        "transcripts": list(raw_transcripts),
    }


def _duration_seconds(segments: list[TranscriptSegment]) -> float | None:
    if not segments:
        return None
    return max(segment.start + segment.duration for segment in segments)

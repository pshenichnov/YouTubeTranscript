"""Request and response schemas for the HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtractTranscriptRequest(BaseModel):
    """Input for extracting transcripts from one YouTube video."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "video": "https://youtu.be/dQw4w9WgXcQ",
                    "languages": ["en", "de"],
                    "timestamps": False,
                    "saveToFiles": True,
                    "outputDir": "Scripts",
                }
            ]
        },
    )

    video: str = Field(
        ...,
        min_length=1,
        description="YouTube video ID or supported YouTube URL.",
    )
    languages: list[str] | None = Field(
        default=None,
        description=(
            "Optional language codes to restrict extraction. When omitted, every "
            "available transcript language is extracted."
        ),
    )
    timestamps: bool = Field(
        default=False,
        description="When true, each text line is prefixed with a [mm:ss] timestamp.",
    )
    save_to_files: bool = Field(
        default=True,
        alias="saveToFiles",
        description="When true, transcript text is saved using the CLI-compatible file layout.",
    )
    output_dir: str = Field(
        default="Scripts",
        alias="outputDir",
        description="Base folder used when saveToFiles is true.",
    )


class TranscriptSegmentResponse(BaseModel):
    """One timed transcript snippet."""

    text: str = Field(description="Transcript text for this snippet.")
    start: float = Field(description="Start time in seconds from the beginning of the video.")
    duration: float = Field(description="Snippet duration in seconds.")


class ExtractedTranscriptResponse(BaseModel):
    """Formatted transcript for one language."""

    language: str = Field(description="Transcript language code.")
    text: str = Field(description="Formatted full transcript text.")
    segments: list[TranscriptSegmentResponse] = Field(
        description="Original timed transcript snippets."
    )
    saved_path: str | None = Field(
        default=None,
        alias="savedPath",
        description="Saved transcript file path, or null when saveToFiles is false.",
    )


class TranscriptExtractionResponse(BaseModel):
    """Completed transcript extraction response."""

    completed: bool = Field(
        default=True,
        description="Always true for this synchronous endpoint; 200 OK means extraction finished.",
    )
    video_id: str = Field(alias="videoId", description="Canonical YouTube video ID.")
    title: str | None = Field(description="Best-effort video title used for saved folder names.")
    saved: bool = Field(description="Whether transcript files were written.")
    transcript_count: int = Field(
        alias="transcriptCount",
        description="Number of transcript languages returned.",
    )
    transcripts: list[ExtractedTranscriptResponse] = Field(
        description="Extracted transcripts, one entry per language."
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(description="Human-readable error message.")

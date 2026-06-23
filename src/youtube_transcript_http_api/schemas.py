"""Request and response schemas for the HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CreateVideoRequest(BaseModel):
    """Input for extracting and storing one YouTube video's transcripts."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "dQw4w9WgXcQ",
                    "timestamps": False,
                    "thumbnail": False,
                }
            ]
        },
    )

    id: str = Field(
        ...,
        min_length=1,
        description="YouTube video ID or supported YouTube URL.",
    )
    timestamps: bool = Field(
        default=False,
        description="When true, saved transcript text uses [mm:ss] timestamp lines.",
    )
    thumbnail: bool = Field(
        default=False,
        description="When true, also saves the video thumbnail.",
    )


class VideoMetadataResponse(BaseModel):
    """Compact per-video metadata returned by the API."""

    video_id: str = Field(alias="videoId", description="Canonical YouTube video ID.")
    video_title: str | None = Field(
        alias="videoTitle",
        description="Best-effort public video title.",
    )
    video_url: str = Field(alias="videoUrl", description="Canonical YouTube watch URL.")
    video_length_seconds: float | None = Field(
        alias="videoLengthSeconds",
        description="Video length derived from available transcript segment timings.",
    )
    transcripts: list[str] = Field(
        description="Language codes for transcripts extracted and saved for this video.",
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(description="Human-readable error message.")

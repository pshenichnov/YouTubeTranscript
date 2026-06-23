"""FastAPI application for YouTube transcript extraction."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, status

import youtube_transcript.service as service
from youtube_transcript.models import InvalidVideoInput, TranscriptError, TranscriptUnavailable

from .schemas import (
    ErrorResponse,
    ExtractedTranscriptResponse,
    ExtractTranscriptRequest,
    TranscriptExtractionResponse,
    TranscriptSegmentResponse,
)

API_TITLE = "YouTube Transcript API"
API_VERSION = "0.1.0"
API_DESCRIPTION = """
Extract text transcripts from YouTube videos by ID or URL.

The initial extraction endpoint is synchronous: a `200 OK` response means
transcript retrieval, formatting, and optional file saving have finished.
"""


def create_app() -> FastAPI:
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        contact={
            "name": "YouTubeTranscript",
        },
        openapi_tags=[
            {
                "name": "Health",
                "description": "Basic service health checks.",
            },
            {
                "name": "Transcripts",
                "description": "Transcript extraction from YouTube videos.",
            },
        ],
    )

    @app.get(
        "/health",
        tags=["Health"],
        summary="Check API health",
        description="Returns a lightweight status response when the API process is running.",
    )
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/transcripts/extract",
        tags=["Transcripts"],
        summary="Extract transcripts",
        description=(
            "Synchronously extracts one video's transcripts. The response is returned only "
            "after transcripts are fetched, formatted, and optionally saved to disk."
        ),
        response_model=TranscriptExtractionResponse,
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "model": ErrorResponse,
                "description": "The video input is not a valid YouTube ID or URL.",
            },
            status.HTTP_404_NOT_FOUND: {
                "model": ErrorResponse,
                "description": "No transcript was available for the video or requested languages.",
            },
            status.HTTP_500_INTERNAL_SERVER_ERROR: {
                "model": ErrorResponse,
                "description": "The API could not complete extraction or save transcript files.",
            },
        },
    )
    def extract_transcripts(
        request: ExtractTranscriptRequest,
    ) -> TranscriptExtractionResponse:
        languages = tuple(request.languages) if request.languages else None

        try:
            result = service.extract_transcripts(
                request.video,
                languages=languages,
                timestamps=request.timestamps,
                save_to_files=request.save_to_files,
                output_dir=request.output_dir,
            )
        except InvalidVideoInput as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except TranscriptUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"could not write transcript: {exc}",
            ) from exc
        except TranscriptError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        transcripts = [
            ExtractedTranscriptResponse(
                language=transcript.language,
                text=transcript.text,
                segments=[
                    TranscriptSegmentResponse(
                        text=segment.text,
                        start=segment.start,
                        duration=segment.duration,
                    )
                    for segment in transcript.segments
                ],
                savedPath=str(transcript.saved_path) if transcript.saved_path else None,
            )
            for transcript in result.transcripts
        ]

        return TranscriptExtractionResponse(
            completed=True,
            videoId=result.video_id,
            title=result.title,
            saved=any(transcript.saved_path is not None for transcript in result.transcripts),
            transcriptCount=len(result.transcripts),
            transcripts=transcripts,
        )

    return app


app = create_app()

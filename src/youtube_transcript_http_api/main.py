"""FastAPI application for YouTube transcript extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse

import youtube_transcript.service as service
from youtube_transcript.models import InvalidVideoInput, TranscriptError, TranscriptUnavailable
from youtube_transcript.parsing import extract_video_id
from youtube_transcript.storage import DEFAULT_OUTPUT_DIR

from .schemas import CreateVideoRequest, ErrorResponse, VideoMetadataResponse

API_TITLE = "YouTube Transcript API"
API_VERSION = "0.1.0"
API_DESCRIPTION = """
Extract and store YouTube video transcripts.

`POST /videos` is synchronous: a `200 OK` response means transcript retrieval,
formatting, optional thumbnail saving, and metadata saving have finished.
"""

_LANGUAGE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


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
                "name": "Videos",
                "description": "Video extraction and saved video artifacts.",
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
        "/videos",
        tags=["Videos"],
        summary="Extract video transcripts",
        description=(
            "Synchronously extracts all available transcripts for a video, saves them "
            "to disk, optionally saves the thumbnail, and returns compact metadata."
        ),
        response_model=VideoMetadataResponse,
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "model": ErrorResponse,
                "description": "The video input is not a valid YouTube ID or URL.",
            },
            status.HTTP_404_NOT_FOUND: {
                "model": ErrorResponse,
                "description": "No transcript was available for the video.",
            },
            status.HTTP_500_INTERNAL_SERVER_ERROR: {
                "model": ErrorResponse,
                "description": "The API could not complete extraction or save files.",
            },
        },
    )
    def create_video(request: CreateVideoRequest) -> dict[str, object]:
        try:
            result = service.extract_transcripts(
                request.id,
                timestamps=request.timestamps,
                save_to_files=True,
                save_thumbnail_file=request.thumbnail,
                output_dir=DEFAULT_OUTPUT_DIR,
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
                detail=f"could not write video artifacts: {exc}",
            ) from exc
        except TranscriptError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        if result.metadata_path is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="metadata was not saved",
            )

        return _read_metadata(result.metadata_path)

    @app.get(
        "/videos/{id}/thumbnail",
        tags=["Videos"],
        summary="Get saved thumbnail",
        description="Returns the saved JPEG thumbnail for a video.",
        response_class=FileResponse,
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "model": ErrorResponse,
                "description": "The video ID is invalid.",
            },
            status.HTTP_404_NOT_FOUND: {
                "model": ErrorResponse,
                "description": "The thumbnail file has not been saved.",
            },
        },
    )
    def get_thumbnail(id: str) -> FileResponse:
        video_id = _validated_video_id(id)
        path = _video_dir(video_id) / f"{video_id}.jpg"
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="thumbnail not found",
            )
        return FileResponse(path, media_type="image/jpeg")

    @app.get(
        "/videos/{id}/metadata",
        tags=["Videos"],
        summary="Get saved metadata",
        description="Returns the saved compact metadata JSON for a video.",
        response_model=VideoMetadataResponse,
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "model": ErrorResponse,
                "description": "The video ID is invalid.",
            },
            status.HTTP_404_NOT_FOUND: {
                "model": ErrorResponse,
                "description": "The metadata file has not been saved.",
            },
        },
    )
    def get_metadata(id: str) -> dict[str, object]:
        video_id = _validated_video_id(id)
        path = _metadata_path(video_id)
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="metadata not found",
            )
        return _read_metadata(path)

    @app.get(
        "/videos/{id}/{language}",
        tags=["Videos"],
        summary="Get saved transcript text",
        description="Returns the saved transcript text for one video language.",
        response_class=PlainTextResponse,
        responses={
            status.HTTP_400_BAD_REQUEST: {
                "model": ErrorResponse,
                "description": "The video ID or language is invalid.",
            },
            status.HTTP_404_NOT_FOUND: {
                "model": ErrorResponse,
                "description": "The transcript file has not been saved.",
            },
        },
    )
    def get_transcript(id: str, language: str) -> PlainTextResponse:
        video_id = _validated_video_id(id)
        if not _LANGUAGE_RE.match(language):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid transcript language",
            )

        path = _video_dir(video_id) / f"{video_id}.{language}.txt"
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="transcript not found",
            )
        return PlainTextResponse(path.read_text(encoding="utf-8"))

    return app


def _validated_video_id(value: str) -> str:
    try:
        return extract_video_id(value)
    except InvalidVideoInput as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def _video_dir(video_id: str) -> Path:
    return Path(DEFAULT_OUTPUT_DIR) / video_id


def _metadata_path(video_id: str) -> Path:
    return _video_dir(video_id) / f"{video_id}.metadata.json"


def _read_metadata(path: Path) -> dict[str, object]:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"could not read metadata: {exc}",
        ) from exc

    if not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="metadata file is not a JSON object",
        )
    return metadata


app = create_app()

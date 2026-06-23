"""Tests for the FastAPI transcript API. No network."""

from pathlib import Path

from fastapi.testclient import TestClient

import youtube_transcript.service as service
from youtube_transcript.models import InvalidVideoInput, TranscriptSegment, TranscriptUnavailable
from youtube_transcript.service import ExtractedTranscript, TranscriptExtractionResult
from youtube_transcript_http_api.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_openapi_describes_transcript_endpoint():
    response = _client().get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"] == "YouTube Transcript API"
    assert "/transcripts/extract" in spec["paths"]
    assert spec["paths"]["/transcripts/extract"]["post"]["summary"] == "Extract transcripts"


def test_extract_transcripts_returns_completed_result(monkeypatch):
    def fake_extract_transcripts(
        video,
        *,
        languages,
        timestamps,
        save_to_files,
        output_dir,
    ):
        assert video == "https://youtu.be/dQw4w9WgXcQ"
        assert languages == ("en",)
        assert timestamps is True
        assert save_to_files is False
        assert output_dir == "Scripts"
        return TranscriptExtractionResult(
            video_id="dQw4w9WgXcQ",
            title="Greeting",
            transcripts=[
                ExtractedTranscript(
                    language="en",
                    text="[00:00] hello",
                    segments=[TranscriptSegment(text="hello", start=0.0, duration=1.0)],
                    saved_path=None,
                )
            ],
        )

    monkeypatch.setattr(service, "extract_transcripts", fake_extract_transcripts)

    response = _client().post(
        "/transcripts/extract",
        json={
            "video": "https://youtu.be/dQw4w9WgXcQ",
            "languages": ["en"],
            "timestamps": True,
            "saveToFiles": False,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "completed": True,
        "videoId": "dQw4w9WgXcQ",
        "title": "Greeting",
        "saved": False,
        "transcriptCount": 1,
        "transcripts": [
            {
                "language": "en",
                "text": "[00:00] hello",
                "segments": [{"text": "hello", "start": 0.0, "duration": 1.0}],
                "savedPath": None,
            }
        ],
    }


def test_extract_transcripts_reports_saved_paths(monkeypatch):
    monkeypatch.setattr(
        service,
        "extract_transcripts",
        lambda *args, **kwargs: TranscriptExtractionResult(
            video_id="dQw4w9WgXcQ",
            title=None,
            transcripts=[
                ExtractedTranscript(
                    language="en",
                    text="hello",
                    segments=[TranscriptSegment(text="hello", start=0.0, duration=1.0)],
                    saved_path=Path("Scripts/video/dQw4w9WgXcQ.en.txt"),
                )
            ],
        ),
    )

    response = _client().post("/transcripts/extract", json={"video": "dQw4w9WgXcQ"})

    assert response.status_code == 200
    body = response.json()
    assert body["saved"] is True
    assert body["transcripts"][0]["savedPath"] == "Scripts/video/dQw4w9WgXcQ.en.txt"


def test_extract_transcripts_maps_domain_errors(monkeypatch):
    monkeypatch.setattr(
        service,
        "extract_transcripts",
        lambda *args, **kwargs: (_ for _ in ()).throw(InvalidVideoInput("bad video")),
    )

    response = _client().post("/transcripts/extract", json={"video": "bad"})

    assert response.status_code == 400
    assert response.json() == {"detail": "bad video"}


def test_extract_transcripts_maps_unavailable_transcripts(monkeypatch):
    monkeypatch.setattr(
        service,
        "extract_transcripts",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            TranscriptUnavailable("no transcripts")
        ),
    )

    response = _client().post("/transcripts/extract", json={"video": "dQw4w9WgXcQ"})

    assert response.status_code == 404
    assert response.json() == {"detail": "no transcripts"}

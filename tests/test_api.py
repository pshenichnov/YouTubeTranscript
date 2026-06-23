"""Tests for the FastAPI video API. No network."""

from pathlib import Path

from fastapi.testclient import TestClient

import youtube_transcript.service as service
import youtube_transcript_http_api.main as api_main
from youtube_transcript.models import InvalidVideoInput, TranscriptSegment, TranscriptUnavailable
from youtube_transcript.service import ExtractedTranscript, TranscriptExtractionResult


def _client() -> TestClient:
    return TestClient(api_main.create_app())


def test_openapi_describes_video_endpoints():
    response = _client().get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"] == "YouTube Transcript API"
    assert "/videos" in spec["paths"]
    assert "/videos/{id}/{language}" in spec["paths"]
    assert "/videos/{id}/thumbnail" in spec["paths"]
    assert "/videos/{id}/metadata" in spec["paths"]
    assert spec["paths"]["/videos"]["post"]["summary"] == "Extract video transcripts"


def test_post_videos_extracts_and_returns_metadata(monkeypatch, tmp_path):
    metadata_path = tmp_path / "dQw4w9WgXcQ" / "dQw4w9WgXcQ.metadata.json"
    metadata_path.parent.mkdir()
    metadata_path.write_text(
        """
{
  "videoId": "dQw4w9WgXcQ",
  "videoTitle": "Greeting",
  "videoUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "videoLengthSeconds": 1.0,
  "transcripts": ["en"]
}
""".strip(),
        encoding="utf-8",
    )

    def fake_extract_transcripts(
        video,
        *,
        timestamps,
        save_to_files,
        save_thumbnail_file,
        output_dir,
    ):
        assert video == "https://youtu.be/dQw4w9WgXcQ"
        assert timestamps is True
        assert save_to_files is True
        assert save_thumbnail_file is True
        assert output_dir == "Scripts"
        return TranscriptExtractionResult(
            video_id="dQw4w9WgXcQ",
            title="Greeting",
            transcripts=[
                ExtractedTranscript(
                    language="en",
                    text="[00:00] hello",
                    segments=[TranscriptSegment(text="hello", start=0.0, duration=1.0)],
                    saved_path=Path("Scripts/dQw4w9WgXcQ/dQw4w9WgXcQ.en.txt"),
                )
            ],
            metadata_path=metadata_path,
            thumbnail_path=Path("Scripts/dQw4w9WgXcQ/dQw4w9WgXcQ.jpg"),
        )

    monkeypatch.setattr(service, "extract_transcripts", fake_extract_transcripts)

    response = _client().post(
        "/videos",
        json={
            "id": "https://youtu.be/dQw4w9WgXcQ",
            "timestamps": True,
            "thumbnail": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "videoId": "dQw4w9WgXcQ",
        "videoTitle": "Greeting",
        "videoUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "videoLengthSeconds": 1.0,
        "transcripts": ["en"],
    }


def test_post_videos_maps_domain_errors(monkeypatch):
    monkeypatch.setattr(
        service,
        "extract_transcripts",
        lambda *args, **kwargs: (_ for _ in ()).throw(InvalidVideoInput("bad video")),
    )

    response = _client().post(
        "/videos",
        json={"id": "bad", "timestamps": False, "thumbnail": False},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "bad video"}


def test_post_videos_maps_unavailable_transcripts(monkeypatch):
    monkeypatch.setattr(
        service,
        "extract_transcripts",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            TranscriptUnavailable("no transcripts")
        ),
    )

    response = _client().post(
        "/videos",
        json={"id": "dQw4w9WgXcQ", "timestamps": False, "thumbnail": False},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "no transcripts"}


def test_get_video_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DEFAULT_OUTPUT_DIR", str(tmp_path))
    folder = tmp_path / "dQw4w9WgXcQ"
    folder.mkdir()
    (folder / "dQw4w9WgXcQ.en.txt").write_text("hello world", encoding="utf-8")
    (folder / "dQw4w9WgXcQ.jpg").write_bytes(b"jpeg-bytes")
    (folder / "dQw4w9WgXcQ.metadata.json").write_text(
        """
{
  "videoId": "dQw4w9WgXcQ",
  "videoTitle": "Greeting",
  "videoUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "videoLengthSeconds": 1.0,
  "transcripts": ["en"]
}
""".strip(),
        encoding="utf-8",
    )
    client = _client()

    transcript = client.get("/videos/dQw4w9WgXcQ/en")
    thumbnail = client.get("/videos/dQw4w9WgXcQ/thumbnail")
    metadata = client.get("/videos/dQw4w9WgXcQ/metadata")

    assert transcript.status_code == 200
    assert transcript.text == "hello world"
    assert transcript.headers["content-type"].startswith("text/plain")
    assert thumbnail.status_code == 200
    assert thumbnail.content == b"jpeg-bytes"
    assert thumbnail.headers["content-type"] == "image/jpeg"
    assert metadata.status_code == 200
    assert metadata.json()["transcripts"] == ["en"]


def test_get_video_artifacts_return_404_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(api_main, "DEFAULT_OUTPUT_DIR", str(tmp_path))

    assert _client().get("/videos/dQw4w9WgXcQ/en").status_code == 404
    assert _client().get("/videos/dQw4w9WgXcQ/thumbnail").status_code == 404
    assert _client().get("/videos/dQw4w9WgXcQ/metadata").status_code == 404

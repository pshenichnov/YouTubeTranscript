"""Tests for the reusable extraction service. No network."""

import json

import youtube_transcript.service as service
from youtube_transcript.models import TranscriptSegment

_SEGMENTS = [
    TranscriptSegment(text="hello", start=0.0, duration=1.0),
    TranscriptSegment(text="world", start=1.0, duration=1.0),
]


def test_extract_transcripts_formats_and_saves(monkeypatch, tmp_path):
    def fake_fetch_all(video_id, languages):
        assert video_id == "dQw4w9WgXcQ"
        assert languages == ("en",)
        return {"en": _SEGMENTS}

    monkeypatch.setattr(service, "fetch_all_transcripts", fake_fetch_all)
    monkeypatch.setattr(service, "fetch_video_title", lambda video_id: "Greeting")
    monkeypatch.setattr(
        service,
        "fetch_video_thumbnail",
        lambda video_id: b"jpeg-bytes",
    )

    result = service.extract_transcripts(
        "https://youtu.be/dQw4w9WgXcQ",
        languages=("en",),
        save_thumbnail_file=True,
        output_dir=tmp_path,
    )

    assert result.video_id == "dQw4w9WgXcQ"
    assert result.title == "Greeting"
    assert len(result.transcripts) == 1
    transcript = result.transcripts[0]
    assert transcript.language == "en"
    assert transcript.text == "hello world"
    assert transcript.segments == _SEGMENTS

    folder = tmp_path / "dQw4w9WgXcQ"
    assert transcript.saved_path == folder / "dQw4w9WgXcQ.en.txt"
    assert transcript.saved_path.read_text(encoding="utf-8") == "hello world"
    assert result.metadata_path == folder / "dQw4w9WgXcQ.metadata.json"
    assert result.thumbnail_path == folder / "dQw4w9WgXcQ.jpg"
    assert result.thumbnail_path.read_bytes() == b"jpeg-bytes"

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata == {
        "videoId": "dQw4w9WgXcQ",
        "videoTitle": "Greeting",
        "videoUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "videoLengthSeconds": 2.0,
        "transcripts": ["en"],
    }


def test_extract_transcripts_can_skip_file_saving(monkeypatch, tmp_path):
    monkeypatch.setattr(
        service,
        "fetch_all_transcripts",
        lambda video_id, languages: {"en": _SEGMENTS},
    )
    monkeypatch.setattr(service, "fetch_video_title", lambda video_id: None)

    result = service.extract_transcripts(
        "dQw4w9WgXcQ",
        timestamps=True,
        save_to_files=False,
        output_dir=tmp_path,
    )

    assert result.transcripts[0].text == "[00:00] hello\n[00:01] world"
    assert result.transcripts[0].saved_path is None
    assert result.metadata_path is None
    assert result.thumbnail_path is None
    assert not list(tmp_path.iterdir())

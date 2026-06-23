"""Tests for the CLI's status-only console contract. No network."""

from datetime import date

import youtube_transcript.service as service
import youtube_transcript_cli.cli as cli
from youtube_transcript.models import TranscriptSegment, TranscriptUnavailable

_SEGMENTS = [
    TranscriptSegment(text="hello", start=0.0, duration=1.0),
    TranscriptSegment(text="world", start=1.0, duration=1.0),
]


def _patch_pipeline(monkeypatch, *, transcripts=None, fetch_error=None, title=None):
    def fake_fetch_all(video_id, languages):
        if fetch_error is not None:
            raise fetch_error
        return transcripts

    monkeypatch.setattr(service, "fetch_all_transcripts", fake_fetch_all)
    monkeypatch.setattr(service, "fetch_video_title", lambda video_id: title)


def test_success_saves_one_file_per_language(monkeypatch, tmp_path, capsys):
    _patch_pipeline(
        monkeypatch,
        transcripts={"en": _SEGMENTS, "de": _SEGMENTS},
        title="Greeting",
    )
    rc = cli.main(["dQw4w9WgXcQ", "-o", str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert out.startswith("success:")
    assert "2" in out and "en" in out and "de" in out
    # Transcript text must NOT appear on the console.
    assert "hello" not in out and "world" not in out

    folder = tmp_path / f"{date.today().isoformat()}-Greeting"
    assert (folder / "dQw4w9WgXcQ.en.txt").read_text(encoding="utf-8") == "hello world"
    assert (folder / "dQw4w9WgXcQ.de.txt").read_text(encoding="utf-8") == "hello world"


def test_failure_prints_failed_to_stderr(monkeypatch, tmp_path, capsys):
    _patch_pipeline(
        monkeypatch,
        fetch_error=TranscriptUnavailable("transcripts are disabled"),
    )
    rc = cli.main(["dQw4w9WgXcQ", "-o", str(tmp_path)])
    captured = capsys.readouterr()

    assert rc == 1
    assert captured.err.startswith("failed:")
    assert "transcripts are disabled" in captured.err
    assert captured.out == ""


def test_invalid_input_fails_without_network(monkeypatch, tmp_path, capsys):
    # No pipeline patch needed: parsing rejects this before fetching runs.
    monkeypatch.setattr(
        service, "fetch_all_transcripts", lambda *a, **k: _must_not_be_called()
    )
    rc = cli.main(["not a valid id !!!", "-o", str(tmp_path)])
    assert rc == 1
    assert capsys.readouterr().err.startswith("failed:")


def _must_not_be_called():  # pragma: no cover - guard, must never run
    raise AssertionError("fetch_all_transcripts should not be called for invalid input")

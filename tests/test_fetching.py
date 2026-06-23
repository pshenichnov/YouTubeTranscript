"""Tests for the network boundary.

Per the design rule, these mock *only* at the ``youtube_transcript_api``
boundary — the only third-party seam the rest of the package is allowed to know
about. No real network access happens here.
"""

from dataclasses import dataclass

import pytest
from requests.exceptions import SSLError
from youtube_transcript_api._errors import CouldNotRetrieveTranscript

from youtube_transcript.fetching import (
    fetch_all_transcripts,
    fetch_transcript,
    fetch_video_thumbnail,
    fetch_video_title,
)
from youtube_transcript.models import TranscriptSegment, TranscriptUnavailable


@dataclass
class _FakeSnippet:
    text: str
    start: float
    duration: float


class _FakeTranscript:
    """Stand-in for a single ``Transcript`` in a ``TranscriptList``."""

    def __init__(self, language_code, snippets):
        self.language_code = language_code
        self._snippets = snippets

    def fetch(self):
        return self._snippets


class _FakeApi:
    """Stand-in for ``YouTubeTranscriptApi``; ``fetch``/``list`` are scripted."""

    def __init__(self, *, result=None, error=None, transcripts=None):
        self._result = result
        self._error = error
        self._transcripts = transcripts or []

    def fetch(self, video_id, languages):
        if self._error is not None:
            raise self._error
        return self._result

    def list(self, video_id):
        if self._error is not None:
            raise self._error
        return list(self._transcripts)


def _patch_api(monkeypatch, **kwargs):
    monkeypatch.setattr(
        "youtube_transcript_api.YouTubeTranscriptApi",
        lambda: _FakeApi(**kwargs),
    )


def test_maps_snippets_to_segments(monkeypatch):
    _patch_api(
        monkeypatch,
        result=[
            _FakeSnippet(text="hello", start=0.0, duration=1.5),
            _FakeSnippet(text="world", start=1.5, duration=2.0),
        ],
    )
    segments = fetch_transcript("abcdefghijk")
    assert segments == [
        TranscriptSegment(text="hello", start=0.0, duration=1.5),
        TranscriptSegment(text="world", start=1.5, duration=2.0),
    ]


def test_could_not_retrieve_becomes_transcript_unavailable(monkeypatch):
    _patch_api(monkeypatch, error=CouldNotRetrieveTranscript("abcdefghijk"))
    with pytest.raises(TranscriptUnavailable):
        fetch_transcript("abcdefghijk")


def test_transport_error_becomes_transcript_unavailable(monkeypatch):
    # An SSL failure (e.g. a corporate proxy's cert not trusted) must surface as
    # our own error, not leak the raw requests traceback.
    _patch_api(monkeypatch, error=SSLError("certificate verify failed"))
    with pytest.raises(TranscriptUnavailable) as excinfo:
        fetch_transcript("abcdefghijk")
    assert "network error" in str(excinfo.value)


def test_fetch_all_returns_every_language(monkeypatch):
    _patch_api(
        monkeypatch,
        transcripts=[
            _FakeTranscript("en", [_FakeSnippet("hello", 0.0, 1.0)]),
            _FakeTranscript("de", [_FakeSnippet("hallo", 0.0, 1.0)]),
        ],
    )
    result = fetch_all_transcripts("abcdefghijk")
    assert list(result) == ["en", "de"]
    assert result["en"] == [TranscriptSegment(text="hello", start=0.0, duration=1.0)]
    assert result["de"] == [TranscriptSegment(text="hallo", start=0.0, duration=1.0)]


def test_fetch_all_filters_to_requested_languages(monkeypatch):
    _patch_api(
        monkeypatch,
        transcripts=[
            _FakeTranscript("en", [_FakeSnippet("hello", 0.0, 1.0)]),
            _FakeTranscript("de", [_FakeSnippet("hallo", 0.0, 1.0)]),
            _FakeTranscript("fr", [_FakeSnippet("salut", 0.0, 1.0)]),
        ],
    )
    result = fetch_all_transcripts("abcdefghijk", languages=["de"])
    assert list(result) == ["de"]


def test_fetch_all_raises_when_no_requested_language_available(monkeypatch):
    _patch_api(
        monkeypatch,
        transcripts=[_FakeTranscript("en", [_FakeSnippet("hello", 0.0, 1.0)])],
    )
    with pytest.raises(TranscriptUnavailable):
        fetch_all_transcripts("abcdefghijk", languages=["zz"])


def test_fetch_all_translates_disabled_error(monkeypatch):
    _patch_api(monkeypatch, error=CouldNotRetrieveTranscript("abcdefghijk"))
    with pytest.raises(TranscriptUnavailable):
        fetch_all_transcripts("abcdefghijk")


def test_fetch_all_translates_transport_error(monkeypatch):
    _patch_api(monkeypatch, error=SSLError("certificate verify failed"))
    with pytest.raises(TranscriptUnavailable) as excinfo:
        fetch_all_transcripts("abcdefghijk")
    assert "network error" in str(excinfo.value)


class _FakeResponse:
    def __init__(self, payload=None, *, status_code=200, content=b""):
        self.status_code = status_code
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_video_title_returns_title(monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *a, **k: _FakeResponse({"title": "  My Great Video  "}),
    )
    assert fetch_video_title("abcdefghijk") == "My Great Video"


def test_fetch_video_title_none_on_network_error(monkeypatch):
    def boom(*a, **k):
        raise SSLError("certificate verify failed")

    monkeypatch.setattr("requests.get", boom)
    assert fetch_video_title("abcdefghijk") is None


def test_fetch_video_title_none_on_missing_title(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse({}))
    assert fetch_video_title("abcdefghijk") is None


def test_fetch_video_thumbnail_returns_maxres_image(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _FakeResponse(status_code=200, content=b"jpeg-bytes")

    monkeypatch.setattr("requests.get", fake_get)

    assert fetch_video_thumbnail("abcdefghijk") == b"jpeg-bytes"
    assert calls == ["https://i.ytimg.com/vi/abcdefghijk/maxresdefault.jpg"]


def test_fetch_video_thumbnail_falls_back_to_hqdefault(monkeypatch):
    responses = [
        _FakeResponse(status_code=404, content=b""),
        _FakeResponse(status_code=200, content=b"fallback-jpeg"),
    ]

    monkeypatch.setattr("requests.get", lambda *a, **k: responses.pop(0))

    assert fetch_video_thumbnail("abcdefghijk") == b"fallback-jpeg"


def test_fetch_video_thumbnail_raises_when_unavailable(monkeypatch):
    monkeypatch.setattr(
        "requests.get",
        lambda *a, **k: _FakeResponse(status_code=404, content=b""),
    )

    with pytest.raises(TranscriptUnavailable):
        fetch_video_thumbnail("abcdefghijk")

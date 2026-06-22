"""The network boundary: the only module that talks to YouTube.

All third-party (`youtube_transcript_api`) usage is contained here and its
errors are translated into our own `TranscriptUnavailable`, so the rest of the
package — and the tests — never import or mock the library elsewhere.
"""

from __future__ import annotations

from collections.abc import Sequence

from .models import TranscriptSegment, TranscriptUnavailable

# Languages to try, in order of preference, when the caller doesn't specify.
DEFAULT_LANGUAGES = ("en",)


def fetch_transcript(
    video_id: str,
    languages: Sequence[str] = DEFAULT_LANGUAGES,
) -> list[TranscriptSegment]:
    """Fetch a transcript for ``video_id`` in the most preferred available language.

    Args:
        video_id: a canonical 11-char ID (see :mod:`parsing`).
        languages: language codes in order of preference.

    Raises:
        TranscriptUnavailable: transcript is disabled, missing, the video is
            unavailable/private, the request was blocked by YouTube, or the
            network/transport itself failed (DNS, connection, TLS, timeout).
    """
    # Imported lazily so importing this module (and the pure layers that don't
    # call it) never requires the dependency to be installed.
    from requests.exceptions import RequestException
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import CouldNotRetrieveTranscript

    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=list(languages))
    except CouldNotRetrieveTranscript as exc:
        raise TranscriptUnavailable(str(exc).strip()) from exc
    except RequestException as exc:
        # Transport failure before YouTube could answer (e.g. no network, or a
        # corporate proxy's TLS interception failing cert verification). Translate
        # it like any other retrieval failure instead of leaking a raw traceback.
        raise TranscriptUnavailable(f"network error fetching transcript: {exc}") from exc

    return _to_segments(fetched)


def _to_segments(fetched) -> list[TranscriptSegment]:
    """Map the third-party snippet objects to our own segment type."""
    return [
        TranscriptSegment(text=s.text, start=s.start, duration=s.duration)
        for s in fetched
    ]


def fetch_all_transcripts(
    video_id: str,
    languages: Sequence[str] | None = None,
) -> dict[str, list[TranscriptSegment]]:
    """Fetch every available transcript for ``video_id``, keyed by language code.

    Args:
        video_id: a canonical 11-char ID (see :mod:`parsing`).
        languages: if given, restrict the result to these language codes; when
            ``None`` (the default) every available language is fetched.

    Returns:
        A mapping of language code -> segments, in the order YouTube lists them.

    Raises:
        TranscriptUnavailable: transcripts are disabled/missing for the video, the
            video is unavailable/private, the request was blocked, the transport
            failed, or ``languages`` was given but none of them are available.
    """
    from requests.exceptions import RequestException
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import CouldNotRetrieveTranscript

    wanted = set(languages) if languages else None

    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
        result: dict[str, list[TranscriptSegment]] = {}
        for transcript in transcript_list:
            code = transcript.language_code
            if wanted is not None and code not in wanted:
                continue
            result[code] = _to_segments(transcript.fetch())
    except CouldNotRetrieveTranscript as exc:
        raise TranscriptUnavailable(str(exc).strip()) from exc
    except RequestException as exc:
        raise TranscriptUnavailable(f"network error fetching transcript: {exc}") from exc

    if not result:
        if wanted is not None:
            raise TranscriptUnavailable(
                f"no transcript available in requested language(s): {', '.join(languages)}"
            )
        raise TranscriptUnavailable("no transcripts available for this video")

    return result


# YouTube's oEmbed endpoint returns lightweight public metadata (incl. the title)
# without an API key. Used only to name the output folder (see storage.py).
_OEMBED_URL = "https://www.youtube.com/oembed"


def fetch_video_title(video_id: str) -> str | None:
    """Best-effort lookup of a video's title, for naming the output folder.

    Returns the title string, or ``None`` if it cannot be determined (network
    failure, non-200, or unexpected payload). Callers must treat ``None`` as a
    soft miss and fall back to the video ID — a title failure never aborts an
    otherwise successful run.
    """
    import requests
    from requests.exceptions import RequestException

    params = {"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"}
    try:
        resp = requests.get(_OEMBED_URL, params=params, timeout=10)
        resp.raise_for_status()
        title = resp.json().get("title")
    except (RequestException, ValueError):
        return None

    if not isinstance(title, str) or not title.strip():
        return None
    return title.strip()

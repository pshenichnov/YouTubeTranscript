from youtube_transcript.formatting import to_plain_text, to_timestamped
from youtube_transcript.models import TranscriptSegment

SEGMENTS = [
    TranscriptSegment(text="Hello there", start=0.0, duration=2.0),
    TranscriptSegment(text="general\nkenobi", start=2.5, duration=1.5),
    TranscriptSegment(text="  spaced  ", start=65.0, duration=1.0),
]


def test_plain_text_joins_and_collapses_newlines():
    assert to_plain_text(SEGMENTS) == "Hello there general kenobi spaced"


def test_plain_text_empty():
    assert to_plain_text([]) == ""


def test_timestamped_lines():
    assert to_timestamped(SEGMENTS) == (
        "[00:00] Hello there\n"
        "[00:02] general kenobi\n"
        "[01:05] spaced"
    )


def test_timestamp_includes_hours_past_one_hour():
    seg = TranscriptSegment(text="x", start=3661.0, duration=1.0)
    assert to_timestamped([seg]) == "[1:01:01] x"

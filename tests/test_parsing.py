import pytest

from youtube_transcript.models import InvalidVideoInput
from youtube_transcript.parsing import extract_video_id

VALID_ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "value",
    [
        VALID_ID,
        f"  {VALID_ID}  ",
        f"https://www.youtube.com/watch?v={VALID_ID}",
        f"http://youtube.com/watch?v={VALID_ID}&t=42s",
        f"https://m.youtube.com/watch?v={VALID_ID}",
        f"https://youtu.be/{VALID_ID}",
        f"youtu.be/{VALID_ID}?t=10",
        f"https://www.youtube.com/embed/{VALID_ID}",
        f"https://www.youtube.com/shorts/{VALID_ID}",
        f"https://www.youtube.com/live/{VALID_ID}",
        f"https://www.youtube.com/v/{VALID_ID}",
    ],
)
def test_extracts_id(value):
    assert extract_video_id(value) == VALID_ID


def test_extracts_id_from_short_url():
    assert extract_video_id(f"https://youtu.be/{VALID_ID}") == VALID_ID


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        None,
        "not a url",
        "https://example.com/watch?v=" + VALID_ID,  # wrong host
        "https://www.youtube.com/watch?v=tooshort",  # bad id length
        "https://youtu.be/has spaces here",
    ],
)
def test_rejects_invalid(value):
    with pytest.raises(InvalidVideoInput):
        extract_video_id(value)

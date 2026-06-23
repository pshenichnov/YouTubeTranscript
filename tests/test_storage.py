"""Tests for filesystem persistence. No network; writes go to tmp_path."""

import json
from datetime import date

from youtube_transcript.storage import (
    DEFAULT_OUTPUT_DIR,
    MAX_TITLE_LEN,
    build_folder_name,
    sanitize_title,
    save_metadata,
    save_thumbnail,
    save_transcript,
)

_ON = date(2026, 1, 2)


def test_sanitize_strips_illegal_chars_and_collapses_whitespace():
    assert sanitize_title('a/b:c "d"  e') == "abc d e"


def test_sanitize_trims_trailing_dot_and_space():
    assert sanitize_title("My Video. ") == "My Video"


def test_sanitize_caps_length():
    assert len(sanitize_title("x" * 200)) == MAX_TITLE_LEN


def test_sanitize_unusable_title_becomes_empty():
    assert sanitize_title("///") == ""


def test_folder_name_uses_video_id():
    assert build_folder_name("abcdefghijk", "My: Video", on=_ON) == "abcdefghijk"


def test_folder_name_ignores_missing_or_unusable_title():
    assert build_folder_name("abcdefghijk", None, on=_ON) == "abcdefghijk"
    assert build_folder_name("abcdefghijk", "???", on=_ON) == "abcdefghijk"


def test_save_uses_video_id_folder_and_language_file(tmp_path):
    path = save_transcript(
        "hello world",
        video_id="abcdefghijk",
        language="en",
        title="My Great Video",
        output_dir=tmp_path,
        on=_ON,
    )
    assert path == tmp_path / "abcdefghijk" / "abcdefghijk.en.txt"
    assert path.read_text(encoding="utf-8") == "hello world"


def test_save_separate_file_per_language_same_folder(tmp_path):
    en = save_transcript("hi", video_id="vid01234567", language="en",
                         title="T", output_dir=tmp_path, on=_ON)
    de = save_transcript("hallo", video_id="vid01234567", language="de",
                         title="T", output_dir=tmp_path, on=_ON)
    assert en.parent == de.parent
    assert en.name == "vid01234567.en.txt"
    assert de.name == "vid01234567.de.txt"
    assert en.read_text(encoding="utf-8") == "hi"
    assert de.read_text(encoding="utf-8") == "hallo"


def test_save_falls_back_to_video_id_when_no_title(tmp_path):
    path = save_transcript("body", video_id="abcdefghijk", language="en",
                          title=None, output_dir=tmp_path, on=_ON)
    assert path == tmp_path / "abcdefghijk" / "abcdefghijk.en.txt"


def test_save_is_idempotent_and_overwrites(tmp_path):
    save_transcript("first", video_id="abcdefghijk", language="en",
                   output_dir=tmp_path, on=_ON)
    path = save_transcript("second", video_id="abcdefghijk", language="en",
                          output_dir=tmp_path, on=_ON)
    assert path.read_text(encoding="utf-8") == "second"


def test_save_creates_missing_output_dir(tmp_path):
    out = tmp_path / "nested" / "Scripts"
    assert not out.exists()
    path = save_transcript("x", video_id="abcdefghijk", language="en", output_dir=out)
    assert path.exists()


def test_save_thumbnail_uses_video_id_folder_and_jpg_file(tmp_path):
    path = save_thumbnail(b"jpeg-bytes", video_id="abcdefghijk", output_dir=tmp_path)

    assert path == tmp_path / "abcdefghijk" / "abcdefghijk.jpg"
    assert path.read_bytes() == b"jpeg-bytes"


def test_save_metadata_uses_video_metadata_json_file(tmp_path):
    path = save_metadata(
        {"videoTitle": "Привет", "transcripts": ["ru"]},
        video_id="abcdefghijk",
        output_dir=tmp_path,
    )

    assert path == tmp_path / "abcdefghijk" / "abcdefghijk.metadata.json"
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "videoTitle": "Привет",
        "transcripts": ["ru"],
    }


def test_default_output_dir_constant():
    assert DEFAULT_OUTPUT_DIR == "Scripts"

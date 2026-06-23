"""Command-line entry point. Wires arguments to the shared service layer."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from youtube_transcript.models import TranscriptError
from youtube_transcript.service import extract_transcripts
from youtube_transcript.storage import DEFAULT_OUTPUT_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="youtube-transcript",
        description="Extract a text transcript from a YouTube video.",
    )
    parser.add_argument("video", help="YouTube video ID or URL")
    parser.add_argument(
        "-l",
        "--language",
        action="append",
        dest="languages",
        metavar="CODE",
        help=(
            "Restrict to this language code (repeatable). When omitted, every "
            "available language is pulled, one file per language."
        ),
    )
    parser.add_argument(
        "-t",
        "--timestamps",
        action="store_true",
        help="Prefix each line with a [mm:ss] timestamp.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        metavar="DIR",
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Folder to save the transcript into. A per-video subfolder is "
            f"created inside it. Defaults to '{DEFAULT_OUTPUT_DIR}'."
        ),
    )
    return parser


def _enable_utf8(stream: object) -> None:
    """Best-effort: make ``stream`` tolerate non-ASCII output."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def main(argv: Sequence[str] | None = None) -> int:
    _enable_utf8(sys.stdout)
    _enable_utf8(sys.stderr)

    args = build_parser().parse_args(argv)
    languages = tuple(args.languages) if args.languages else None

    try:
        result = extract_transcripts(
            args.video,
            languages=languages,
            timestamps=args.timestamps,
            output_dir=args.output_dir,
        )
    except TranscriptError as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"failed: could not write transcript: {exc}", file=sys.stderr)
        return 1

    codes = ", ".join(transcript.language for transcript in result.transcripts)
    saved_paths = [
        transcript.saved_path
        for transcript in result.transcripts
        if transcript.saved_path is not None
    ]
    folder = saved_paths[0].parent if saved_paths else args.output_dir
    print(f"success: saved {len(saved_paths)} language(s) [{codes}] to {folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

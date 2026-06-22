"""Command-line entry point. Wires parsing -> fetching -> formatting."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .fetching import fetch_all_transcripts, fetch_video_title
from .formatting import to_plain_text, to_timestamped
from .models import TranscriptError
from .parsing import extract_video_id
from .storage import DEFAULT_OUTPUT_DIR, save_transcript


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
    """Best-effort: make ``stream`` tolerate non-ASCII output.

    Status lines can embed a saved path containing the video title (e.g. emoji or
    non-Latin script). On a legacy Windows console (cp1252) ``print`` would raise
    ``UnicodeEncodeError``; switching to UTF-8 with ``errors="replace"`` renders it
    on capable terminals and degrades gracefully elsewhere instead of crashing.
    """
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
        video_id = extract_video_id(args.video)
        transcripts = fetch_all_transcripts(video_id, languages=languages)
    except TranscriptError as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 1

    format_segments = to_timestamped if args.timestamps else to_plain_text
    title = fetch_video_title(video_id)  # best-effort; falls back to the ID

    try:
        saved = [
            save_transcript(
                format_segments(segments),
                video_id=video_id,
                language=code,
                title=title,
                output_dir=args.output_dir,
            )
            for code, segments in transcripts.items()
        ]
    except OSError as exc:
        print(f"failed: could not write transcript: {exc}", file=sys.stderr)
        return 1

    codes = ", ".join(transcripts)
    folder = saved[0].parent
    print(f"success: saved {len(saved)} language(s) [{codes}] to {folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

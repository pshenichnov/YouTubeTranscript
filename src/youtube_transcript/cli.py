"""Compatibility wrapper for the renamed CLI package."""

from __future__ import annotations

from youtube_transcript_cli.cli import build_parser, main

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

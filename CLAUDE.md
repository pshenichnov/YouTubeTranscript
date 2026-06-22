# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

A Python tool that extracts text transcripts from YouTube videos given a video ID
(e.g. `dQw4w9WgXcQ`) or any common YouTube URL. Output is either one plain-text
block or timestamped lines. Usable as a CLI or as a library.

## Architecture

The package lives in `src/youtube_transcript/` and is split by concern, layered so
that only one module touches the network:

- **`models.py`** — pure domain types (`TranscriptSegment`) and the error hierarchy
  (`TranscriptError` → `InvalidVideoInput`, `TranscriptUnavailable`). Everything else
  depends on this; it imports nothing project-specific and nothing third-party.
- **`parsing.py`** — `extract_video_id()` normalizes a bare ID or any URL form
  (`watch?v=`, `youtu.be/`, `/embed/`, `/shorts/`, `/v/`, `/live/`) to a canonical
  11-char ID. Pure and network-free; the most heavily tested layer.
- **`fetching.py`** — `fetch_transcript()` (single language), `fetch_all_transcripts()`
  (every available language, keyed by code), and `fetch_video_title()`. **The only
  module that contacts YouTube.** All `youtube_transcript_api` usage (imported lazily)
  is confined here, and its errors — plus `requests` transport errors — are translated
  into our `TranscriptUnavailable`. Nothing else imports or mocks the third-party library.
- **`formatting.py`** — `to_plain_text()` / `to_timestamped()`, pure functions from
  segments to strings.
- **`storage.py`** — `sanitize_title()` / `build_folder_name()` (pure) and
  `save_transcript()`. Writes one file per language to
  `<output-dir>/<yyyy-mm-dd>-<video-title-or-id>/<video_id>.<lang>.txt` (folder
  name carries the extraction date). The only filesystem-writing module;
  `output-dir` defaults to `Scripts/`.
- **`cli.py`** — `main()` wires parsing → fetching → formatting → persistence.
  The transcript is saved to disk (see `storage.py`), never printed; the console
  shows status only — `success: <info>` (with the saved path) on stdout, or
  `failed: <message>` on stderr + exit code 1.

**The core design rule:** parsing and formatting stay pure, so the test suite runs
fully offline and the network is isolated to a single, swappable module. Preserve this
boundary — don't import `youtube_transcript_api` outside `fetching.py`.

## Commands

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Run the tool (also saves to <output-dir>/<title-or-id>/<id>.txt; -o defaults to Scripts)
.\.venv\Scripts\python.exe -m youtube_transcript <video-id-or-url> [-l CODE]... [-t] [-o DIR]

# Tests
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests/test_parsing.py::test_extracts_id_from_short_url

# Lint / format
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format .
```

## Conventions

- Targets Python 3.9+ (`from __future__ import annotations` is used so `X | None`
  syntax works on 3.9). Keep new code compatible.
- Tests for the pure layers must not hit the network. When testing `fetching.py`, mock
  at the `youtube_transcript_api` boundary only.
- Language preference is explicit: `fetch_transcript` takes an ordered `languages`
  tuple (default `("en",)`); don't silently grab whichever transcript comes first.

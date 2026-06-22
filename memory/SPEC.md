# YouTube Transcript — Project Specification

## 1. Overview

A Python tool that extracts text transcripts from YouTube videos. The caller
supplies either a bare 11-character video ID (e.g. `dQw4w9WgXcQ`) or any common
YouTube URL, and the tool returns the transcript as either one plain-text block
or as timestamped lines. It is usable both as a **CLI** and as an importable
**library**.

- Package name: `youtube-transcript` (version `0.1.0`)
- Source layout: `src/youtube_transcript/`
- Python: **3.9+** (`from __future__ import annotations` used so `X | None`
  syntax works on 3.9)
- Build backend: `hatchling`
- Runtime dependency: `youtube-transcript-api>=1.0`
- Dev dependencies: `pytest>=8.0`, `ruff>=0.6`

## 2. Design Principles

1. **Single network boundary.** Only `fetching.py` contacts YouTube and only it
   imports `youtube_transcript_api` (imported lazily inside the function). No
   other module — and no test outside the fetching tests — imports or mocks the
   third-party library.
2. **Pure parsing and formatting.** `parsing.py` and `formatting.py` are pure and
   network-free, so the bulk of the test suite runs fully offline.
3. **Layered dependency direction.** `models.py` depends on nothing
   project-specific or third-party; every other module depends on it.
4. **Explicit language preference.** Transcripts are selected by an ordered
   `languages` tuple (default `("en",)`), never "whichever comes first."
5. **Deliberate error translation.** Third-party errors are caught at the network
   boundary and re-raised as the package's own `TranscriptError` subtypes.

## 3. Module Specification

### 3.1 `models.py` — domain types & errors
- `TranscriptSegment` — frozen dataclass: `text: str`, `start: float` (seconds
  from video start), `duration: float` (seconds shown).
- Error hierarchy:
  - `TranscriptError(Exception)` — base for every deliberately-raised error.
  - `InvalidVideoInput(TranscriptError)` — input is neither a valid ID nor a
    parseable URL.
  - `TranscriptUnavailable(TranscriptError)` — no transcript could be retrieved
    (disabled, missing, private, blocked, etc.).
- Imports nothing project-specific and nothing third-party.

### 3.2 `parsing.py` — input → canonical video ID
- `extract_video_id(value: str) -> str` — normalize a bare ID or any common
  YouTube URL to a canonical 11-char ID. Raises `InvalidVideoInput` on failure
  (including `None` and empty/whitespace input).
- Canonical ID = exactly 11 chars from `[A-Za-z0-9_-]`.
- Supported URL forms:
  - `watch?v=<id>` (query param)
  - `youtu.be/<id>`
  - `/embed/<id>`, `/shorts/<id>`, `/v/<id>`, `/live/<id>` (path prefixes)
- Tolerates URLs pasted without a scheme (e.g. `youtu.be/abc...`).
- Pure and network-free; the most heavily unit-tested layer.

### 3.3 `fetching.py` — the network boundary
- `fetch_transcript(video_id, languages=DEFAULT_LANGUAGES) -> list[TranscriptSegment]`
  — single most-preferred language; `DEFAULT_LANGUAGES = ("en",)`.
- `fetch_all_transcripts(video_id, languages=None) -> dict[str, list[TranscriptSegment]]`
  — fetch **every** available transcript keyed by language code (in the order
  YouTube lists them). When `languages` is given, restrict to those codes;
  raise `TranscriptUnavailable` if none of them are available.
- Lazily imports `YouTubeTranscriptApi` and `CouldNotRetrieveTranscript`; uses
  `api.list(video_id)` to enumerate languages and `transcript.fetch()` per
  language. Catches `CouldNotRetrieveTranscript` and `requests` transport errors
  and re-raises as `TranscriptUnavailable`.
- Maps each fetched snippet to a `TranscriptSegment`.
- Also exposes `fetch_video_title()` for naming the output subfolder (§3.6) —
  this stays inside the network boundary; the title lookup is best-effort and a
  failure must not abort an otherwise successful run.

### 3.4 `formatting.py` — segments → text (pure)
- `to_plain_text(segments) -> str` — join segment text into one space-separated
  block; newlines inside a segment collapsed to spaces; result stripped.
- `to_timestamped(segments) -> str` — one `[mm:ss] text` line per segment;
  switches to `[h:mm:ss]` when the timestamp has an hours component.

### 3.5 `cli.py` — entry point
- `main(argv=None) -> int` wires parsing → fetching → formatting → persistence.
- Args: positional `video` (ID or URL); `-l/--language CODE` (repeatable —
  restrict to these languages; when omitted, **all** available languages are
  pulled); `-t/--timestamps` (flag); `-o/--output-dir DIR` (output folder;
  default `Scripts`).
- On a successful run, **one `.txt` file per language** is always written to disk
  (see §3.6). The transcript text itself is **not** echoed to the console — only
  a status line is printed.
- Console output is status-only:
  - Success: print `success: <info>` (including the saved file path) to stdout
    and return `0`.
  - Failure: on any `TranscriptError` (or a write failure), print
    `failed: <message>` to stderr and return exit code `1`.
- Console script entry point: `youtube-transcript = youtube_transcript.cli:main`.

### 3.6 Output persistence
- After each successful run the result is stored on the filesystem as one or more
  `.txt` files. This is mandatory, not opt-in.
- **Output folder.** Governed by `-o/--output-dir`. When the flag is omitted the
  default folder is `Scripts` (created relative to the current working
  directory). The folder is created if it does not already exist.
- **Per-video subfolder.** Inside the output folder, a separate subfolder named
  `<yyyy-mm-dd>-<video-title>` is created, where `<yyyy-mm-dd>` is the extraction
  date (the date the run happened) and `<video-title>` is a short, filesystem-safe
  title (illegal characters removed, whitespace collapsed, length capped). When a
  title cannot be determined, the canonical 11-char video ID is used in place of
  the title.
- **One file per language.** Each fetched language is written to its own file
  named `<video_id>.<language-code>.txt` inside that subfolder.
- **Title source.** Obtaining the video title is the responsibility of the
  network boundary (`fetching.py`); it must not introduce a second seam to the
  third-party library elsewhere. If the title lookup fails or is unavailable, the
  run still succeeds using the video-ID fallback above.
- File content matches the chosen format (plain text by default, timestamped
  lines with `-t`). Directory creation must be idempotent; re-running for the
  same video/language/date overwrites the file rather than erroring.

## 4. CLI Contract

```
youtube-transcript <video-id-or-url> [-l CODE]... [-t] [-o DIR]
```
- Transcripts are always saved, one file per language, to
  `<output-dir>/<yyyy-mm-dd>-<video-title-or-id>/<video_id>.<lang>.txt`, where
  `<output-dir>` defaults to `Scripts`. Both the output folder and the dated
  per-video subfolder are created as needed. With `-l CODE`, only the named
  languages are saved; otherwise all available ones are. File content is plain
  text by default; timestamped lines with `-t`.
- The console shows status only — never the transcript text:
  - Success: `success: <info>` (with the saved path) on stdout, exit `0`.
  - Failure: `failed: <message>` on stderr, exit `1`.

## 5. Testing Requirements

- Pure layers (`parsing`, `formatting`) must not hit the network.
- When testing `fetching.py`, mock only at the `youtube_transcript_api`
  boundary — nowhere else.
- pytest config: `testpaths = ["tests"]`, `addopts = "-q"`.
- Existing tests: `tests/test_parsing.py`, `tests/test_formatting.py`.

## 6. Tooling & Conventions

- Lint/format with `ruff` (line length 100; lint rules `E, F, I, UP, B`).
- Keep new code compatible with Python 3.9+.
- **Do not import `youtube_transcript_api` outside `fetching.py`** — this is the
  core invariant that keeps the suite offline and the network swappable.

## 7. Environment Notes

- Use a project-local virtualenv; run commands via `.\.venv\Scripts\python.exe`.

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Run
.\.venv\Scripts\python.exe -m youtube_transcript <video-id-or-url> [-l CODE]... [-t]

# Tests / lint
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

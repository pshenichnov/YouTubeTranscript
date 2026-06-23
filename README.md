# youtube-transcript

Extract text transcripts from YouTube videos by video ID or URL.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Usage

```powershell
# Bare video ID or any common YouTube URL — pulls ALL available languages
youtube-transcript dQw4w9WgXcQ
youtube-transcript "https://youtu.be/dQw4w9WgXcQ"

# Restrict to specific languages (repeatable)
youtube-transcript dQw4w9WgXcQ -l de -l en

# Save timestamped lines instead of one text block
youtube-transcript dQw4w9WgXcQ --timestamps

# Also save the video thumbnail
youtube-transcript dQw4w9WgXcQ --thumbnail

# Choose where transcripts are saved (default: ./Scripts)
youtube-transcript dQw4w9WgXcQ -o C:\transcripts
```

Or as a module: `python -m youtube_transcript <video>`.

Transcripts and video metadata are **saved to files**, not printed. Every
available language is pulled (or just the `-l` ones), and each transcript gets a
text file. One metadata JSON file is written per video:

```
<output-dir>/<video-id>/<video-id>.<lang>.txt
<output-dir>/<video-id>/<video-id>.metadata.json
```

When `--thumbnail` is passed, the CLI also saves:

```
<output-dir>/<video-id>/<video-id>.jpg
```

The output folder defaults to `Scripts/` and is created if missing; inside it a
per-video subfolder is named with the video ID. The console prints only a status line:
`success: ...` (with the language count and folder, plus the thumbnail path when
requested) on success, or `failed: ...` on error.

The metadata JSON includes the video ID, title, URL, transcript-derived video
length, and a `transcripts` array with the extracted language codes.

## API

Install API dependencies and start the FastAPI app:

```powershell
pip install -e ".[api]"
youtube-transcript-api
```

Swagger UI is available at <http://127.0.0.1:8000/docs>.

`POST /videos` is synchronous: `200 OK` means fetching, formatting, optional
thumbnail saving, and metadata saving have finished. The response contains only
compact metadata, not transcript text.

Example request:

```json
{
  "id": "dQw4w9WgXcQ",
  "timestamps": false,
  "thumbnail": false
}
```

Available video endpoints:

```text
POST /videos
GET /videos/{id}/{language}
GET /videos/{id}/thumbnail
GET /videos/{id}/metadata
```

### Docker

Build the API image:

```bash
docker build -t youtube-transcript-api .
```

Run the container:

```bash
mkdir -p Scripts
docker run --rm -p 8000:8000 -v "$(pwd)/Scripts:/app/Scripts" youtube-transcript-api
```

Or build and run with Docker Compose:

```bash
mkdir -p Scripts
docker compose up --build
```

Swagger UI will be available at <http://127.0.0.1:8000/docs>. Transcript,
metadata, and optional thumbnail files are written to the host `Scripts/` folder
through the container volume mount.

## Use as a library

```python
from youtube_transcript import (
    extract_video_id,
    fetch_all_transcripts,
    fetch_video_title,
    save_transcript,
    to_plain_text,
)

video_id = extract_video_id("https://youtu.be/dQw4w9WgXcQ")

# Every available language, keyed by code (pass languages=[...] to restrict)
transcripts = fetch_all_transcripts(video_id)
title = fetch_video_title(video_id)

for code, segments in transcripts.items():
    text = to_plain_text(segments)
    path = save_transcript(text, video_id=video_id, language=code, title=title)
    print(code, "->", path)
```

For a single language, use `fetch_transcript(video_id, languages=("en",))`, which
returns the segments for the most-preferred available language.

## Development

```powershell
pytest                                   # run all tests
pytest tests/test_parsing.py::test_extracts_id_from_short_url   # single test
ruff check .                             # lint
ruff format .                            # format
```

The parsing and formatting layers are pure (no network), so the test suite runs
fully offline. The only module that contacts YouTube is `fetching.py`.

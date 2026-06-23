# YouTubeTranscript API Plan

## Goal

Expose the existing YouTube transcript functionality through both a command-line
application and an HTTP API without duplicating the core workflow.

## Proposed Project Structure

- `youtube_transcript`
  - Core library package.
  - Owns parsing, fetching, formatting, storage, models, and reusable transcript
    extraction orchestration.
- `youtube_transcript_cli`
  - Console application package.
  - Replaces the current direct CLI implementation while preserving the existing
    `youtube-transcript` command behavior.
- `youtube_transcript_api`
  - Future FastAPI application package.
  - Exposes Swagger/OpenAPI documentation and HTTP endpoints.

## Shared Core

Add a reusable service layer to the core package. It should:

- Accept a YouTube video ID or URL.
- Normalize it to a canonical video ID.
- Fetch all available transcripts or only requested languages.
- Format transcript output as plain text or timestamped text.
- Optionally save transcript files using the existing folder/file layout.
- Return structured results that can be consumed by both CLI and API callers.
- Raise the existing domain errors where possible so CLI and API can map them to
  their own output formats.

## CLI First

The first implementation step is to move console-specific code into a dedicated
CLI package while keeping current behavior intact.

Required compatibility guarantees:

- `youtube-transcript ...` continues to work.
- `python -m youtube_transcript ...` continues to work.
- Console output remains status-only:
  - success goes to stdout
  - failures go to stderr
  - transcript text is saved to files, not printed
- Default output layout remains:

```text
Scripts/<yyyy-mm-dd>-<video-title-or-id>/<video-id>.<language>.txt
```

## Future API

Use FastAPI for the API project because it provides Swagger/OpenAPI generation
from typed request and response models.

Recommended initial endpoints:

- `GET /health`
- `POST /transcripts/extract`

`POST /transcripts/extract` should initially be synchronous:

- `200 OK` means extraction finished successfully.
- `400 Bad Request` for invalid video input.
- `404 Not Found` for unavailable transcripts or requested languages.
- `502 Bad Gateway` for upstream/network retrieval failures if distinguishable.
- `500 Internal Server Error` for unexpected failures.

An async job model can be added later if the API needs long-running extraction,
batch processing, retries, or persistent job history.

## Swagger Documentation

The API should include:

- Title, description, and version metadata.
- Tags for endpoint grouping.
- Endpoint summaries and descriptions.
- Typed request and response schemas.
- Documented error responses.

## Test Strategy

- Keep existing CLI behavior tests.
- Add tests for the shared service layer.
- Later, add API tests using FastAPI's test client to verify:
  - OpenAPI generation.
  - Successful extraction responses with mocked fetching.
  - Language filtering.
  - Timestamp formatting.
  - Error-to-status-code mapping.

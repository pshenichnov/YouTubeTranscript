"""Run the API with ``python -m youtube_transcript_http_api``."""

from __future__ import annotations


def main() -> None:
    import os

    import uvicorn

    uvicorn.run(
        "youtube_transcript_http_api.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()

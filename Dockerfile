FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir ".[api]"

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/Scripts \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "youtube_transcript_http_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

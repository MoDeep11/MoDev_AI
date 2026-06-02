FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY main.py ./main.py
COPY modev ./modev

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[ai]"

RUN useradd --create-home --shell /bin/sh appuser \
    && mkdir -p /app/.modev-output \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

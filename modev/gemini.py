from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from modev.models import GeneratedItem


class GeminiGenerationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or load_env_value("GOOGLE_API_KEY") or load_env_value("GEMINI_API_KEY")
        self.model = model or load_env_value("GEMINI_MODEL") or "models/gemini-2.5-flash"
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY is required in .env")

    def generate(self, system_prompt: str, user_prompt: str) -> list[GeneratedItem]:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "google-genai is not installed. Install it with: uv pip install -e '.[ai]'"
            ) from exc

        client = genai.Client(api_key=self.api_key)
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
        except Exception as exc:
            raise _normalize_gemini_error(exc) from exc

        try:
            return parse_generated_items(response.text or "")
        except ValueError as exc:
            raise GeminiGenerationError("GEMINI_RESPONSE_INVALID_JSON", str(exc)) from exc


def parse_generated_items(raw_text: str) -> list[GeneratedItem]:
    payload = _parse_json_object(raw_text)
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("Gemini response must contain an items array")

    items = [GeneratedItem.from_dict(item) for item in raw_items if isinstance(item, dict)]
    if len(items) != len(raw_items):
        raise ValueError("Every generated item must be an object")
    _validate_unique_paths(items)
    return items


def load_env_value(key: str, env_path: Path | str = ".env") -> str | None:
    if os.getenv(key):
        return os.getenv(key)

    path = Path(env_path)
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return None


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Gemini response is not valid JSON") from None
        value = json.loads(raw_text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Gemini response must be a JSON object")
    return value


def _validate_unique_paths(items: list[GeneratedItem]) -> None:
    seen: set[str] = set()
    for item in items:
        if item.path in seen:
            raise ValueError(f"Duplicate generated path: {item.path}")
        seen.add(item.path)


def _normalize_gemini_error(exc: Exception) -> GeminiGenerationError:
    raw_message = str(exc)
    status = raw_message[:220]
    if "429" in raw_message or "RESOURCE_EXHAUSTED" in raw_message:
        return GeminiGenerationError(
            "GEMINI_QUOTA_EXCEEDED",
            "Gemini API 할당량이 초과되었습니다. 요금제/쿼터를 확인하거나 잠시 후 다시 시도해 주세요.",
        )
    if "timeout" in raw_message.lower() or "deadline" in raw_message.lower():
        return GeminiGenerationError(
            "GEMINI_TIMEOUT",
            "Gemini API 응답 시간이 초과되었습니다. 다시 시도해 주세요.",
        )
    if "500" in raw_message or "503" in raw_message or "INTERNAL" in raw_message:
        return GeminiGenerationError(
            "GEMINI_SERVER_ERROR",
            "Gemini API 서버 오류가 발생했습니다. 다시 시도해 주세요.",
        )
    return GeminiGenerationError("GEMINI_API_ERROR", status)

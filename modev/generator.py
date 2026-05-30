from __future__ import annotations

import json
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

from modev.gemini import GeminiClient, GeminiGenerationError
from modev.models import GeneratedItem, ProjectRequest, validate_safe_path
from modev.prompts import SYSTEM_PROMPT, render_user_prompt
from modev.rules import build_generation_plan


def generate_project(
    request: ProjectRequest,
    output_dir: Path,
    use_ai: bool = True,
) -> tuple[list[GeneratedItem], Path]:
    plan = build_generation_plan(request)
    if use_ai:
        items = GeminiClient().generate(SYSTEM_PROMPT, render_user_prompt(request, plan))
        _ensure_plan_coverage(items, plan.directories, plan.required_files)
    else:
        items = _plan_only_items(plan.directories, plan.required_files)

    project_dir = output_dir / request.project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
    _write_items(project_dir, items)
    return items, project_dir


def stream_generation_events(
    request: ProjectRequest,
    output_dir: Path,
    use_ai: bool = True,
    include_connected: bool = True,
) -> Iterator[dict[str, object]]:
    if include_connected:
        yield {
            "event": "connected",
            "data": {
                "projectId": request.project_id,
                "message": "연결되었습니다. 생성을 시작합니다.",
            },
        }
    try:
        yield {"event": "progress", "data": {"step": "analyzing", "message": "선택된 스택을 분석 중입니다..."}}
        plan = build_generation_plan(request)
        yield {"event": "progress", "data": {"step": "generating", "message": "프로젝트 구조를 생성 중입니다..."}}
        if use_ai:
            items = GeminiClient().generate(SYSTEM_PROMPT, render_user_prompt(request, plan))
            _ensure_plan_coverage(items, plan.directories, plan.required_files)
        else:
            items = _plan_only_items(plan.directories, plan.required_files)

        project_dir = output_dir / request.project_id
        if project_dir.exists():
            shutil.rmtree(project_dir)
        _write_items(project_dir, items)

        total_files = 0
        total_directories = 0
        for item in items:
            if item.type == "file":
                total_files += 1
            else:
                total_directories += 1
            yield {
                "event": "file_created",
                "data": {
                    "type": item.type,
                    "path": item.path,
                    "depth": item.depth,
                    "content": item.content,
                },
            }

        yield {
            "event": "complete",
            "data": {
                "projectId": request.project_id,
                "totalFiles": total_files,
                "totalDirectories": total_directories,
                "projectPath": str(project_dir),
                "message": "프로젝트 구조 생성이 완료되었습니다.",
            },
        }
    except GeminiGenerationError as exc:
        yield {
            "event": "error",
            "data": {
                "code": exc.code,
                "message": str(exc),
            },
        }
    except Exception as exc:
        yield {
            "event": "error",
            "data": {
                "code": "GENERATION_FAILED",
                "message": str(exc),
            },
        }


def new_project_id() -> str:
    return uuid.uuid4().hex[:8]


def _write_items(project_dir: Path, items: list[GeneratedItem]) -> None:
    for item in items:
        validate_safe_path(item.path)
        target = project_dir / item.path
        if item.type == "directory":
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item.content or "", encoding="utf-8")


def _ensure_plan_coverage(items: list[GeneratedItem], directories: list[str], files: list[str]) -> None:
    generated = {item.path for item in items}
    missing_directories = sorted(set(directories) - generated)
    missing_files = sorted(set(files) - generated)
    if missing_directories or missing_files:
        detail = {
            "missing_directories": missing_directories,
            "missing_files": missing_files,
        }
        raise ValueError(f"Gemini response missed required plan items: {json.dumps(detail, ensure_ascii=False)}")


def _plan_only_items(directories: list[str], files: list[str]) -> list[GeneratedItem]:
    items = [GeneratedItem(type="directory", path=path) for path in directories]
    items.extend(
        GeneratedItem(
            type="file",
            path=path,
            content=f"# Generated placeholder for {path}\n\nAI generation was skipped.\n",
        )
        for path in files
    )
    return items

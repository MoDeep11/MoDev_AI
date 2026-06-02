from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Path as ApiPath, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from modev.gemini import load_env_value
from modev.generator import stream_generation_events
from modev.models import Dependency, ProjectRequest, TechStack


OUTPUT_DIR = Path(".modev-output")

app = FastAPI(title="MoDev AI Structure Generator")
known_projects: set[str] = set()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(
            {"code": "VALIDATION_ERROR", "message": "입력값 유효성 오류입니다.", "details": exc.errors()}
        ),
    )


class FieldDto(BaseModel):
    name: str = Field(min_length=1)


class TechStackDto(BaseModel):
    name: str = Field(min_length=1)
    version: str | None = None


class DependencyDto(BaseModel):
    name: str = Field(min_length=1)
    tech_stack_name: str | None = Field(default=None, alias="techStackName")


class GenerateStructureRequest(BaseModel):
    project_id: str = Field(alias="projectId", min_length=1)
    project_name: str = Field(alias="projectName", min_length=1)
    fields: list[FieldDto] = Field(min_length=1)
    tech_stacks: list[TechStackDto] = Field(alias="techStacks", min_length=1)
    dependencies: list[DependencyDto] = Field(default_factory=list)

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str) -> str:
        if "/" in value or "\\" in value or ".." in value:
            raise ValueError("projectId contains unsafe characters")
        return value


class RegenerateStructureRequest(BaseModel):
    project_name: str = Field(alias="projectName", min_length=1)
    fields: list[FieldDto] = Field(min_length=1)
    tech_stacks: list[TechStackDto] = Field(alias="techStacks", min_length=1)
    dependencies: list[DependencyDto] = Field(default_factory=list)


def verify_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header(alias="X-Internal-API-Key")] = None,
) -> None:
    expected = load_env_value("INTERNAL_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "AUTH_MISCONFIGURED", "message": "INTERNAL_API_KEY is not configured."},
        )
    if x_internal_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "유효하지 않은 Internal API Key입니다."},
        )


@app.post("/ai/structures/generate", dependencies=[Depends(verify_internal_api_key)])
def generate_structure(payload: GenerateStructureRequest) -> StreamingResponse:
    request = _to_project_request(payload.project_id, payload)
    return _sse_response(request)


@app.post("/ai/structures/{projectId}/regenerate", dependencies=[Depends(verify_internal_api_key)])
def regenerate_structure(
    payload: RegenerateStructureRequest,
    projectId: Annotated[str, ApiPath(min_length=1)],
) -> StreamingResponse:
    if "/" in projectId or "\\" in projectId or ".." in projectId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": "projectId contains unsafe characters"},
        )
    if projectId not in known_projects and not (OUTPUT_DIR / projectId).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "프로젝트 ID를 찾을 수 없습니다."},
        )
    known_projects.add(projectId)
    request = _to_project_request(projectId, payload)
    return _sse_response(request)


def _sse_response(request: ProjectRequest) -> StreamingResponse:
    def event_stream():
        for event in stream_generation_events(
            request,
            OUTPUT_DIR,
            use_ai=_use_ai_generation(),
            include_connected=False,
        ):
            if event["event"] == "complete":
                known_projects.add(request.project_id)
            yield f"event: {event['event']}\n"
            yield f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _use_ai_generation() -> bool:
    value = load_env_value("MODEV_USE_AI")
    if value is None:
        return True
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _to_project_request(
    project_id: str,
    payload: GenerateStructureRequest | RegenerateStructureRequest,
) -> ProjectRequest:
    return ProjectRequest(
        project_id=project_id,
        project_name=payload.project_name,
        description="",
        domains=[field.name for field in payload.fields],
        stacks=[TechStack(name=stack.name, version=stack.version) for stack in payload.tech_stacks],
        dependencies=[
            Dependency(name=dependency.name, tech_stack_name=dependency.tech_stack_name)
            for dependency in payload.dependencies
        ],
    )

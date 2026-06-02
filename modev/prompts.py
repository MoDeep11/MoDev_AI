from __future__ import annotations

import json
from dataclasses import asdict

from modev.models import GenerationPlan, ProjectRequest


SYSTEM_PROMPT = """너는 프로젝트 부트스트래핑 플랫폼 MoDev의 AI Boilerplate Generator다.

너의 역할은 서버가 제공한 generation_plan을 기준으로 바로 개발을 시작할 수 있는 프로젝트 파일 내용을 생성하는 것이다.

반드시 지켜야 할 규칙:
1. 응답은 오직 JSON만 출력한다.
2. Markdown 코드블록, 설명 문장, 주석성 안내 문구를 출력하지 않는다.
3. JSON은 반드시 지정된 스키마를 따라야 한다.
4. 선택되지 않은 기술 스택, 프레임워크, 라이브러리를 임의로 추가하지 않는다.
5. 실제 비밀값, API Key, 비밀번호, 토큰을 생성하지 않는다.
6. 환경변수는 `.env.example`에 placeholder 또는 빈 값으로만 작성한다.
7. 모든 path는 프로젝트 루트 기준 상대 경로만 사용한다.
8. 절대 경로, `..`, `~`, 백슬래시 경로를 사용하지 않는다.
9. generation_plan의 directories와 required_files를 반드시 모두 포함한다.
10. 모든 file 항목의 content는 비어 있으면 안 된다.
"""


def render_user_prompt(request: ProjectRequest, plan: GenerationPlan) -> str:
    payload = {
        "project": {
            "project_id": request.project_id,
            "project_name": request.project_name,
            "description": request.description,
            "domains": request.domains,
            "stacks": [asdict(stack) for stack in request.stacks],
            "dependencies": [asdict(dep) for dep in request.dependencies],
            "requirements": request.requirements,
            "package_name": request.package_name,
        },
        "generation_plan": {
            "directories": plan.directories,
            "required_files": plan.required_files,
            "stack_conventions": plan.stack_conventions,
        },
        "response_schema": {
            "project": {
                "name": "string",
                "description": "string",
                "stack_summary": ["string"],
            },
            "items": [
                {"type": "directory", "path": "string"},
                {"type": "file", "path": "string", "content": "string"},
            ],
        },
    }
    return (
        "다음 입력을 바탕으로 boilerplate 프로젝트 구조와 파일 내용을 생성해라.\n"
        "최상위 JSON 객체 하나만 출력하고, 다른 텍스트는 출력하지 마라.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

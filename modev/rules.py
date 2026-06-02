from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import PurePosixPath

from modev.models import GenerationPlan, ProjectRequest, validate_safe_path


STACKS = {
    "react": {
        "name": "React",
        "layer": "Frontend",
        "base": "frontend",
        "multi_base": "react-app",
        "directories": ["src", "src/components", "src/pages", "src/hooks", "src/utils", "public"],
        "files": ["package.json", "src/main.tsx", "src/App.tsx", "index.html"],
    },
    "next.js": {
        "name": "Next.js",
        "layer": "Frontend",
        "base": "frontend",
        "multi_base": "next-app",
        "directories": ["app", "components", "lib", "public", "styles"],
        "files": ["package.json", "app/page.tsx", "app/layout.tsx", "next.config.js"],
    },
    "spring boot": {
        "name": "Spring Boot",
        "layer": "Backend",
        "base": "backend",
        "multi_base": "spring-service",
        "directories": [
            "src/main/java/{package_path}",
            "src/main/resources",
            "src/test/java/{package_path}",
        ],
        "files": [
            "build.gradle",
            "src/main/resources/application.yml",
            "src/main/java/{package_path}/Application.java",
        ],
    },
    "nestjs": {
        "name": "NestJS",
        "layer": "Backend",
        "base": "backend",
        "multi_base": "nest-service",
        "directories": ["src", "src/modules", "src/common", "src/config", "test"],
        "files": ["package.json", "src/main.ts", "src/app.module.ts"],
    },
    "fastapi": {
        "name": "FastAPI",
        "layer": "Backend",
        "base": "backend",
        "multi_base": "fastapi-service",
        "directories": ["app", "app/routers", "app/models", "app/schemas", "app/core", "tests"],
        "files": ["requirements.txt", "app/main.py", "app/core/config.py"],
    },
    "docker": {
        "name": "Docker",
        "layer": "DevOps",
        "base": "docker",
        "multi_base": "docker",
        "directories": [],
        "files": [],
    },
}


DOMAIN_BASE_DIRECTORIES = {
    "frontend": "frontend",
    "fe": "frontend",
    "backend": "backend",
    "be": "backend",
    "devops": "docker",
}


def build_generation_plan(request: ProjectRequest) -> GenerationPlan:
    normalized_stacks = [_normalize_stack(stack.name) for stack in request.stacks]
    selected_rules = [STACKS[stack] for stack in normalized_stacks if stack in STACKS]
    layer_counts = Counter(rule["layer"] for rule in selected_rules if rule["layer"] in {"Frontend", "Backend"})

    directories: list[str] = ["docs"]
    for domain in request.domains:
        base = DOMAIN_BASE_DIRECTORIES.get(domain.strip().lower())
        if base:
            directories.append(base)
    if "docker" in normalized_stacks or any(rule["layer"] == "DevOps" for rule in selected_rules):
        directories.append("docker")

    stack_conventions: list[dict[str, object]] = []
    required_files = ["README.md", ".gitignore", ".env.example"]

    package_path = request.package_name.replace(".", "/")
    for rule in selected_rules:
        layer = str(rule["layer"])
        base = str(rule["base"])
        if layer in {"Frontend", "Backend"} and layer_counts[layer] > 1:
            base = f"{base}/{rule['multi_base']}"
        directories.append(base)

        stack_dirs = [
            _join(base, template.format(package_path=package_path))
            for template in rule["directories"]
        ]
        stack_files = [
            _join(base, template.format(package_path=package_path))
            for template in rule["files"]
        ]
        directories.extend(stack_dirs)
        required_files.extend(stack_files)
        stack_conventions.append(
            {
                "stack": rule["name"],
                "layer": layer,
                "base_path": base,
                "directories": stack_dirs,
                "files": stack_files,
            }
        )

    if "docker" in normalized_stacks or "docker" in directories:
        required_files.append("docker-compose.yml")

    return GenerationPlan(
        project_id=request.project_id,
        project_name=request.project_name,
        directories=_unique_sorted_paths(directories),
        required_files=_unique_sorted_paths(required_files),
        stack_conventions=stack_conventions,
        stacks=[stack for stack in request.stacks if _normalize_stack(stack.name) in STACKS],
        dependencies=request.dependencies,
    )


def _normalize_stack(stack: str) -> str:
    value = re.sub(r"\s+", " ", stack.strip().lower())
    aliases = {
        "next": "next.js",
        "nextjs": "next.js",
        "springboot": "spring boot",
        "spring": "spring boot",
        "nest": "nestjs",
        "node": "nestjs",
    }
    return aliases.get(value, value)


def _join(base: str, path: str) -> str:
    if not path:
        return base
    return str(PurePosixPath(base, path))


def _unique_sorted_paths(paths: list[str]) -> list[str]:
    unique: dict[str, None] = {}
    for path in paths:
        validate_safe_path(path)
        unique[path] = None
    grouped = defaultdict(list)
    for path in unique:
        grouped[len(PurePosixPath(path).parts)].append(path)
    sorted_paths: list[str] = []
    for depth in sorted(grouped):
        sorted_paths.extend(sorted(grouped[depth]))
    return sorted_paths

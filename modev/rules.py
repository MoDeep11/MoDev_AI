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
    "vue": {
        "name": "Vue",
        "layer": "Frontend",
        "base": "frontend",
        "multi_base": "vue-app",
        "directories": ["src", "src/components", "src/views", "src/router", "src/stores", "public"],
        "files": ["package.json", "src/main.ts", "src/App.vue", "index.html"],
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
    "django": {
        "name": "Django",
        "layer": "Backend",
        "base": "backend",
        "multi_base": "django-service",
        "directories": ["config", "apps", "apps/api", "apps/common", "templates", "static", "tests"],
        "files": ["requirements.txt", "manage.py", "config/settings.py", "config/urls.py"],
    },
    "gin": {
        "name": "Gin",
        "layer": "Backend",
        "base": "backend",
        "multi_base": "gin-service",
        "directories": ["cmd/server", "internal/handlers", "internal/services", "internal/models", "pkg", "tests"],
        "files": ["go.mod", "cmd/server/main.go", "internal/handlers/router.go"],
    },
    "postgresql": {
        "name": "PostgreSQL",
        "layer": "Database",
        "base": "database/postgresql",
        "multi_base": "postgresql",
        "directories": ["init", "migrations", "backups"],
        "files": ["init/001_init.sql", "README.md"],
    },
    "mysql": {
        "name": "MySQL",
        "layer": "Database",
        "base": "database/mysql",
        "multi_base": "mysql",
        "directories": ["init", "migrations", "backups"],
        "files": ["init/001_init.sql", "README.md"],
    },
    "redis": {
        "name": "Redis",
        "layer": "Database",
        "base": "database/redis",
        "multi_base": "redis",
        "directories": ["config", "scripts"],
        "files": ["config/redis.conf", "README.md"],
    },
    "docker": {
        "name": "Docker",
        "layer": "DevOps",
        "base": "docker",
        "multi_base": "docker",
        "directories": [],
        "files": [],
    },
    "kubernetes": {
        "name": "Kubernetes",
        "layer": "DevOps",
        "base": "k8s",
        "multi_base": "kubernetes",
        "directories": ["base", "overlays/dev", "overlays/prod"],
        "files": ["base/deployment.yaml", "base/service.yaml", "base/kustomization.yaml"],
    },
    "ingress-nginx": {
        "name": "ingress-nginx",
        "layer": "DevOps",
        "base": "k8s/ingress-nginx",
        "multi_base": "ingress-nginx",
        "directories": ["manifests"],
        "files": ["manifests/ingress.yaml", "README.md"],
    },
    "langchain": {
        "name": "LangChain",
        "layer": "AI",
        "base": "ai/langchain",
        "multi_base": "langchain",
        "directories": ["chains", "prompts", "retrievers", "tests"],
        "files": ["requirements.txt", "chains/main.py", "prompts/system.md"],
    },
    "openai python sdk": {
        "name": "OpenAI Python SDK",
        "layer": "AI",
        "base": "ai/openai",
        "multi_base": "openai-python",
        "directories": ["clients", "prompts", "tests"],
        "files": ["requirements.txt", "clients/openai_client.py", "prompts/system.md"],
    },
}


DOMAIN_BASE_DIRECTORIES = {
    "frontend": "frontend",
    "fe": "frontend",
    "backend": "backend",
    "be": "backend",
    "database": "database",
    "db": "database",
    "devops": "docker",
    "ai": "ai",
}


def build_generation_plan(request: ProjectRequest) -> GenerationPlan:
    normalized_stacks = [_normalize_stack(stack.name) for stack in request.stacks]
    unsupported = [
        stack.name
        for stack, normalized in zip(request.stacks, normalized_stacks)
        if normalized not in STACKS
    ]
    if unsupported:
        raise ValueError(f"Unsupported stacks: {', '.join(unsupported)}")

    selected_rules = [STACKS[stack] for stack in normalized_stacks if stack in STACKS]
    layer_counts = Counter(rule["layer"] for rule in selected_rules if rule["layer"] in {"Frontend", "Backend"})

    directories: list[str] = ["docs"]
    for domain in request.domains:
        base = DOMAIN_BASE_DIRECTORIES.get(domain.strip().lower())
        if base:
            directories.append(base)
    if "docker" in normalized_stacks or any(rule["layer"] == "DevOps" for rule in selected_rules):
        directories.append("docker")
    if any(rule["layer"] == "Database" for rule in selected_rules):
        directories.append("database")
    if any(rule["layer"] == "AI" for rule in selected_rules):
        directories.append("ai")

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
        stacks=request.stacks,
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
        "postgres": "postgresql",
        "postgresql": "postgresql",
        "k8s": "kubernetes",
        "ingress nginx": "ingress-nginx",
        "ingressnginx": "ingress-nginx",
        "openai": "openai python sdk",
        "openai sdk": "openai python sdk",
        "openai-python": "openai python sdk",
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

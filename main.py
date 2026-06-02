from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from modev.api import app
from modev.generator import new_project_id, stream_generation_events
from modev.models import Dependency, ProjectRequest, TechStack


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MoDev boilerplate without starting an API server.")
    parser.add_argument("--name", required=True, help="Project name")
    parser.add_argument("--description", default="", help="Project description")
    parser.add_argument("--domain", action="append", default=[], help="Development domain. Can be repeated.")
    parser.add_argument("--stack", action="append", default=[], help="Tech stack. Can be repeated.")
    parser.add_argument("--dependency", action="append", default=[], help="Dependency name or name@version. Can be repeated.")
    parser.add_argument("--requirements", default="", help="Extra generation requirements")
    parser.add_argument("--package-name", default="com.example", help="Java package name for Spring Boot")
    parser.add_argument("--output", default=".modev-output", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Skip Gemini and generate placeholders from rules only")
    args = parser.parse_args()

    request = ProjectRequest(
        project_id=new_project_id(),
        project_name=args.name,
        description=args.description,
        domains=args.domain,
        stacks=[TechStack(name=value) for value in args.stack],
        dependencies=[Dependency.from_text(value) for value in args.dependency],
        requirements=args.requirements,
        package_name=args.package_name,
    )

    for event in stream_generation_events(request, Path(args.output), use_ai=not args.dry_run):
        sys.stdout.write(f"event: {event['event']}\n")
        sys.stdout.write(f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

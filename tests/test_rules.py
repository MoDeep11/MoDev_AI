import unittest

from modev.models import Dependency, ProjectRequest, TechStack
from modev.rules import build_generation_plan


class GenerationPlanTests(unittest.TestCase):
    def test_frontend_backend_devops_plan_contains_required_common_paths(self) -> None:
        request = ProjectRequest(
            project_id="test1234",
            project_name="demo",
            description="demo project",
            domains=["Frontend", "Backend", "DevOps"],
            stacks=[TechStack("React"), TechStack("Spring Boot"), TechStack("Docker")],
            dependencies=[Dependency("Spring Web")],
        )

        plan = build_generation_plan(request)

        self.assertIn("frontend", plan.directories)
        self.assertIn("backend", plan.directories)
        self.assertIn("docker", plan.directories)
        self.assertIn("docs", plan.directories)
        self.assertIn("README.md", plan.required_files)
        self.assertIn(".gitignore", plan.required_files)
        self.assertIn(".env.example", plan.required_files)
        self.assertIn("docker-compose.yml", plan.required_files)
        self.assertIn("frontend/package.json", plan.required_files)
        self.assertIn("backend/build.gradle", plan.required_files)

    def test_same_layer_multiple_stacks_are_split(self) -> None:
        request = ProjectRequest(
            project_id="test1234",
            project_name="demo",
            description="demo project",
            domains=["Backend"],
            stacks=[TechStack("Spring Boot"), TechStack("FastAPI")],
        )

        plan = build_generation_plan(request)

        self.assertIn("backend/spring-service", plan.directories)
        self.assertIn("backend/fastapi-service", plan.directories)
        self.assertIn("backend/spring-service/build.gradle", plan.required_files)
        self.assertIn("backend/fastapi-service/requirements.txt", plan.required_files)


if __name__ == "__main__":
    unittest.main()

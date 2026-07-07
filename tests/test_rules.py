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

    def test_seeded_sql_stack_catalog_is_supported(self) -> None:
        request = ProjectRequest(
            project_id="test1234",
            project_name="seed-catalog-demo",
            description="demo project",
            domains=["Backend", "Frontend", "Database", "DevOps", "AI"],
            stacks=[
                TechStack("Spring Boot", "3.5.0"),
                TechStack("NestJS", "11.0.0"),
                TechStack("FastAPI", "0.115.0"),
                TechStack("Django", "5.2.0"),
                TechStack("Gin", "1.10.0"),
                TechStack("React", "19.0.0"),
                TechStack("Next.js", "15.0.0"),
                TechStack("Vue", "3.5.0"),
                TechStack("PostgreSQL", "16"),
                TechStack("MySQL", "8.4"),
                TechStack("Redis", "7.4"),
                TechStack("Docker", "27.0.0"),
                TechStack("Kubernetes", "1.30.0"),
                TechStack("ingress-nginx", "4.11.0"),
                TechStack("LangChain", "0.3.0"),
                TechStack("OpenAI Python SDK", "1.0.0"),
            ],
            dependencies=[
                Dependency("Spring Security", "6.5.0", "Spring Boot"),
                Dependency("Spring Data JPA", "3.5.0", "Spring Boot"),
                Dependency("Spring Validation", "3.5.0", "Spring Boot"),
                Dependency("Nest Config", "4.0.0", "NestJS"),
                Dependency("Nest TypeORM", "11.0.0", "NestJS"),
                Dependency("Uvicorn", "0.34.0", "FastAPI"),
                Dependency("SQLAlchemy", "2.0.0", "FastAPI"),
                Dependency("Django REST framework", "3.15.0", "Django"),
                Dependency("gin-contrib/cors", "1.7.0", "Gin"),
                Dependency("React Router", "7.0.0", "React"),
                Dependency("Zustand", "5.0.0", "React"),
                Dependency("TanStack Query", "5.0.0", "React"),
                Dependency("NextAuth.js", "4.24.0", "Next.js"),
                Dependency("Pinia", "3.0.0", "Vue"),
                Dependency("pgvector", "0.8.0", "PostgreSQL"),
                Dependency("Redis OM Node", "0.4.0", "Redis"),
                Dependency("Helm", "3.15.0", "Kubernetes"),
                Dependency("langchain-openai", "0.2.0", "LangChain"),
                Dependency("tiktoken", "0.7.0", "OpenAI Python SDK"),
            ],
        )

        plan = build_generation_plan(request)

        self.assertIn("backend/django-service", plan.directories)
        self.assertIn("backend/gin-service", plan.directories)
        self.assertIn("frontend/vue-app", plan.directories)
        self.assertIn("database/postgresql", plan.directories)
        self.assertIn("database/mysql", plan.directories)
        self.assertIn("database/redis", plan.directories)
        self.assertIn("k8s", plan.directories)
        self.assertIn("k8s/ingress-nginx", plan.directories)
        self.assertIn("ai/langchain", plan.directories)
        self.assertIn("ai/openai", plan.directories)
        self.assertIn("backend/django-service/manage.py", plan.required_files)
        self.assertIn("backend/gin-service/go.mod", plan.required_files)
        self.assertIn("frontend/vue-app/src/App.vue", plan.required_files)
        self.assertIn("database/postgresql/init/001_init.sql", plan.required_files)
        self.assertIn("k8s/base/deployment.yaml", plan.required_files)
        self.assertIn("ai/openai/clients/openai_client.py", plan.required_files)


if __name__ == "__main__":
    unittest.main()

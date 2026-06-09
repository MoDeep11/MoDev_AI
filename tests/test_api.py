import os
import unittest

from fastapi.testclient import TestClient

from modev.api import app, known_projects
from modev.gemini import load_env_value


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["MODEV_USE_AI"] = "false"
        known_projects.clear()
        self.client = TestClient(app)
        internal_api_key = load_env_value("INTERNAL_API_KEY")
        self.headers = {"X-Internal-API-Key": internal_api_key} if internal_api_key else {}

    def tearDown(self) -> None:
        os.environ.pop("MODEV_USE_AI", None)
        known_projects.clear()

    def test_generate_structure_streams_events(self) -> None:
        response = self.client.post(
            "/ai/structures/generate",
            json={
                "projectId": "proj_abc123",
                "projectName": "my-project",
                "fields": [{"name": "Backend"}, {"name": "Frontend"}],
                "techStacks": [
                    {"name": "Spring Boot", "version": "3.2.1"},
                    {"name": "React", "version": None},
                ],
                "dependencies": [
                    {"name": "Spring Web", "version": None, "techStackName": "Spring Boot"},
                    {"name": "Axios", "version": "1.14.0", "techStackName": "React"},
                ],
            },
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.text
        self.assertIn("event: progress", body)
        self.assertIn('"step": "analyzing"', body)
        self.assertIn("event: file_created", body)
        self.assertIn('"projectId": "proj_abc123"', body)
        self.assertIn('"totalFiles"', body)

    def test_regenerate_unknown_project_returns_404(self) -> None:
        response = self.client.post(
            "/ai/structures/missing/regenerate",
            json={
                "projectName": "my-project",
                "fields": [{"name": "Backend"}],
                "techStacks": [{"name": "Spring Boot", "version": "3.2.1"}],
                "dependencies": [{"name": "Spring Web", "version": None, "techStackName": "Spring Boot"}],
            },
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "NOT_FOUND")

    def test_validation_error_returns_400(self) -> None:
        response = self.client.post("/ai/structures/generate", json={}, headers=self.headers)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")


if __name__ == "__main__":
    unittest.main()

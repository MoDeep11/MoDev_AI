import unittest

from modev.gemini import parse_generated_items


class GeminiParserTests(unittest.TestCase):
    def test_parse_valid_response(self) -> None:
        items = parse_generated_items(
            """
            {
              "project": {"name": "demo"},
              "items": [
                {"type": "directory", "path": "frontend"},
                {"type": "file", "path": "README.md", "content": "# Demo"}
              ]
            }
            """
        )

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].path, "frontend")
        self.assertEqual(items[1].content, "# Demo")

    def test_reject_unsafe_path(self) -> None:
        with self.assertRaises(ValueError):
            parse_generated_items(
                """
                {
                  "items": [
                    {"type": "file", "path": "../secret.txt", "content": "nope"}
                  ]
                }
                """
            )

    def test_reject_duplicate_path(self) -> None:
        with self.assertRaises(ValueError):
            parse_generated_items(
                """
                {
                  "items": [
                    {"type": "file", "path": "README.md", "content": "one"},
                    {"type": "file", "path": "README.md", "content": "two"}
                  ]
                }
                """
            )

    def test_reject_numeric_file_content(self) -> None:
        with self.assertRaises(ValueError):
            parse_generated_items(
                """
                {
                  "items": [
                    {"type": "file", "path": "frontend/src/App.tsx", "content": "16643"}
                  ]
                }
                """
            )

    def test_reject_placeholder_file_content(self) -> None:
        with self.assertRaises(ValueError):
            parse_generated_items(
                """
                {
                  "items": [
                    {"type": "file", "path": "README.md", "content": "string"}
                  ]
                }
                """
            )


if __name__ == "__main__":
    unittest.main()

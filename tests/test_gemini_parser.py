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


if __name__ == "__main__":
    unittest.main()

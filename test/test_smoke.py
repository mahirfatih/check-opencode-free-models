#!/usr/bin/env python3
"""Comprehensive smoke tests for check-opencode-free-models.

Smoke = fastest safety net: does the script actually run, and does the
JSONC normalizer handle the worst case (comments / trailing commas)?

Scope:
    - Script file existence and compilability (py_compile).
    - Module import without errors.
    - jsonc_to_json: clean JSON, commented JSON, trailing comma.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "check-opencode-free-models.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("check_opencode_free_models", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_script_file_exists(self) -> None:
        self.assertTrue(SCRIPT_PATH.is_file(), f"missing: {SCRIPT_PATH}")

    def test_script_compiles(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        compile(source, str(SCRIPT_PATH), "exec")  # raises on syntax error

    def test_module_loads_without_error(self) -> None:
        self.assertTrue(callable(self.mod.jsonc_to_json))
        self.assertTrue(callable(self.mod.fetch_free_ids))
        self.assertTrue(callable(self.mod.read_config_models))
        self.assertTrue(callable(self.mod.build_block))
        self.assertTrue(callable(self.mod.main))

    def test_minimal_valid_json_is_untouched(self) -> None:
        text = '{"a": 1}'
        self.assertEqual(self.mod.jsonc_to_json(text), text)

    def test_line_comment_is_stripped(self) -> None:
        text = "{\n  // opencode free models\n  \"a\": 1\n}"
        self.assertEqual(json.loads(self.mod.jsonc_to_json(text)), {"a": 1})

    def test_block_comment_is_stripped(self) -> None:
        text = "{\n  /* provider config */\n  \"a\": 1\n}"
        self.assertEqual(json.loads(self.mod.jsonc_to_json(text)), {"a": 1})

    def test_trailing_comma_is_stripped(self) -> None:
        text = '{"providers": {"opencode-api": {"models": {"x": {"name": "X"},}}}}'
        self.assertEqual(
            json.loads(self.mod.jsonc_to_json(text)),
            {"providers": {"opencode-api": {"models": {"x": {"name": "X"}}}}},
        )

    def test_comment_like_text_inside_string_is_kept(self) -> None:
        text = '{"url": "http://x/*y*/", "note": "see //docs"}'
        normalized = self.mod.jsonc_to_json(text)
        self.assertEqual(json.loads(normalized)["url"], "http://x/*y*/")
        self.assertEqual(json.loads(normalized)["note"], "see //docs")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Comprehensive sanity tests for check-opencode-free-models.

Sanity = minimum acceptance criteria at the deepest level: the tool's
defined constants are correct, the example configuration can be normalized
as JSONC, and the generated block is valid JSON.

Scope:
    - Constants (PROVIDER, ENDPOINT, EXTRA_FREE).
    - Repo example config (opencode-free-models.config.example.jsonc)
      is valid via jsonc_to_json + json.loads.
    - build_block output is strict JSON.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "check-opencode-free-models.py"
EXAMPLE_CONFIG_PATH = REPO_ROOT / "opencode-free-models.config.example.jsonc"


def load_script_module():
    spec = importlib.util.spec_from_file_location("check_opencode_free_models", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SanityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_provider_constant(self) -> None:
        self.assertEqual(self.mod.PROVIDER, "opencode-api")

    def test_endpoint_is_live_inference(self) -> None:
        self.assertTrue(self.mod.ENDPOINT.startswith("https://opencode.ai/inference"))

    def test_extra_free_is_empty(self) -> None:
        self.assertEqual(self.mod.EXTRA_FREE, set())

    def test_example_config_is_valid_jsonc(self) -> None:
        text = EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8")
        parsed = json.loads(self.mod.jsonc_to_json(text))
        self.assertIn("provider", parsed)
        self.assertEqual(
            parsed["provider"]["opencode-api"]["name"],
            "Opencode API (Free, chat/completions)",
        )

    def test_read_config_models_parses_models_block(self) -> None:
        text = (
            "{\n"
            '  "provider": {\n'
            '    "opencode-api": {\n'
            '      "models": {\n'
            '        "flint-40b-free": { "name": "Flint 40B Free" },\n'
            '        "beam-free": { "name": "Beam Free" }\n'
            "      }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(
            self.mod.read_config_models(text),
            {"flint-40b-free": "Flint 40B Free", "beam-free": "Beam Free"},
        )

    def test_build_block_output_is_strict_json(self) -> None:
        block = self.mod.build_block([("some-free-model", "Some Free")], {"some-free-model": "Renamed"})
        self.assertEqual(json.loads("{" + block + "}"), {"some-free-model": {"name": "Renamed"}})

    def test_build_block_no_trailing_comma(self) -> None:
        block = self.mod.build_block(
            [("a-free", "A"), ("b-free", "B")],
            {"a-free": "A", "b-free": "B"},
        )
        self.assertFalse(block.rstrip().endswith(","))
        self.assertEqual(
            block,
            '        "a-free": { "name": "A" },\n        "b-free": { "name": "B" }',
        )


if __name__ == "__main__":
    unittest.main()

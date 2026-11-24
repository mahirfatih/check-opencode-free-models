#!/usr/bin/env python3
"""Comprehensive unit tests for check-opencode-free-models.

Saf fonksiyon seviyesi testler: jsonc_to_json, read_config_models,
build_block, fetch_free_ids ve main() akislinin mock'larla dogrulanmasi.

Kapsam:
    - jsonc_to_json: yorum, block comment, trailing comma, string literal koruma.
    - read_config_models: config parse + missing-provider hatasi.
    - build_block: join kurallari, name fallback'i.
    - fetch_free_ids: endpoint filtreleri (chat + free) via mock.
    - main(): drift / in-sync / apply akislari via mock.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import urllib.request

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "check-opencode-free-models.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("check_opencode_free_models", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def free_model(mid, name, type_="chat", cost=0):
    return {
        "id": mid,
        "name": name,
        "type": type_,
        "cost": {"text": {"input": {"price": cost}, "output": {"price": cost}}},
    }


class JsoncToJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_minimal_json_unchanged(self):
        self.assertEqual(self.mod.jsonc_to_json('{"a": 1}'), '{"a": 1}')

    def test_line_comment_stripped(self):
        text = '{\n  // opencode free models\n  "a": 1\n}'
        self.assertEqual(json.loads(self.mod.jsonc_to_json(text)), {"a": 1})

    def test_block_comment_stripped(self):
        text = '{\n  /* provider */\n  "a": [1, 2]\n}'
        self.assertEqual(json.loads(self.mod.jsonc_to_json(text)), {"a": [1, 2]})

    def test_trailing_comma_stripped(self):
        text = '{"a": {"b": 1,},}'
        self.assertEqual(json.loads(self.mod.jsonc_to_json(text)), {"a": {"b": 1}})

    def test_string_literal_with_comment_chars_untouched(self):
        text = '{"url": "http://x/*y*/", "note": "see //docs", "path": "a/b"}'
        normalized = self.mod.jsonc_to_json(text)
        self.assertEqual(json.loads(normalized)["url"], "http://x/*y*/")
        self.assertEqual(json.loads(normalized)["note"], "see //docs")
        self.assertEqual(json.loads(normalized)["path"], "a/b")

    def test_escaped_quote_in_string_kept(self):
        text = '{"a": "he said \\"hi\\" ok", "b": 1}'
        normalized = self.mod.jsonc_to_json(text)
        self.assertEqual(json.loads(normalized)["a"], 'he said "hi" ok')
        self.assertEqual(json.loads(normalized)["b"], 1)


class ReadConfigModelsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_parses_opencode_api_block(self):
        text = (
            "{\n"
            '  "provider": {\n'
            '    "opencode-api": {\n'
            '      "models": {\n'
            '        "flint-40b-free": { "name": "Flint 40B Free" },\n'
            '      }\n'
            "    }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(
            self.mod.read_config_models(text),
            {"flint-40b-free": "Flint 40B Free"},
        )

    def test_missing_provider_exits(self):
        with self.assertRaises(SystemExit):
            self.mod.read_config_models('{\n  "provider": {\n    "other": {}\n  }\n}')


class BuildBlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_single_entry(self):
        self.assertEqual(
            self.mod.build_block([("m-free", "M Free")], {"m-free": "M Free"}),
            '        "m-free": { "name": "M Free" }',
        )

    def test_multiple_entries_comma_separated_no_trailing(self):
        block = self.mod.build_block([("a-free", "A"), ("b-free", "B")], {"a-free": "A", "b-free": "B"})
        self.assertEqual(block, '        "a-free": { "name": "A" },\n        "b-free": { "name": "B" }')
        self.assertFalse(block.rstrip().endswith(","))
        self.assertEqual(json.loads("{" + block + "}"), {"a-free": {"name": "A"}, "b-free": {"name": "B"}})

    def test_falls_back_to_live_name(self):
        self.assertEqual(
            self.mod.build_block([("x-free", "X Live")], {}),
            '        "x-free": { "name": "X Live" }',
        )


class FetchFreeIdsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_filters_chat_models_and_zero_cost(self):
        payload = {
            "data": [
                free_model("chat-free", "Chat Free", type_="chat", cost=0),
                free_model("chat-paid", "Chat Paid", type_="chat", cost=3),
                free_model("decision-free", "Jev Free", type_="decision", cost=0),
                free_model("embedding-free", "Embed Free", type_="embedding", cost=0),
            ]
        }
        with mock.patch.object(urllib.request, "urlopen", return_value=FakeResponse(payload)):
            result = self.mod.fetch_free_ids()
        self.assertEqual(result, [("chat-free", "Chat Free")])

    def test_uses_name_fallback_when_missing(self):
        payload = {"data": [{"id": "noname-free", "type": "chat", "cost": {"text": {"input": {"price": 0}, "output": {"price": 0}}}}]}
        with mock.patch.object(urllib.request, "urlopen", return_value=FakeResponse(payload)):
            result = self.mod.fetch_free_ids()
        self.assertEqual(result, [("noname-free", "noname-free")])


class MainFlowTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_script_module()
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.config_path = Path(tmpdir.name) / "opencode.jsonc"

    def _write_config(self, models_block: str) -> None:
        text = (
            "{\n"
            '  "provider": {\n'
            '    "opencode-api": {\n'
            '      "models": {\n'
            f"{models_block}"
            "      }\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        self.config_path.write_text(text, encoding="utf-8")

    def test_in_sync_returns_zero(self):
        self.mod.CONFIG = str(self.config_path)
        self._write_config('        "in-sync-free": { "name": "In Sync Free" },\n')
        self.mod.fetch_free_ids = mock.Mock(return_value=[("in-sync-free", "In Sync Free")])
        old_argv = sys.argv
        sys.argv = ["check-opencode-free-models.py"]
        try:
            self.assertEqual(self.mod.main(), 0)
        finally:
            sys.argv = old_argv

    def test_drift_without_apply_returns_one(self):
        self.mod.CONFIG = str(self.config_path)
        self._write_config('        "stale-free": { "name": "Stale Free" },\n')
        self.mod.fetch_free_ids = mock.Mock(return_value=[("fresh-free", "Fresh Free")])
        old_argv = sys.argv
        sys.argv = ["check-opencode-free-models.py"]
        try:
            self.assertEqual(self.mod.main(), 1)
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()

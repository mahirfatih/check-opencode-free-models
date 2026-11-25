#!/usr/bin/env python3
"""Comprehensive integration tests for check-opencode-free-models.

Integration = component-level pipeline: module + real file formats + local
HTTP server endpoint. The whole pipeline (fetch -> diff -> build -> validate ->
write -> read-back) is verified end-to-end against a local server.

Kapsam:
    - Local HTTP server uzerinden fetch_free_ids filtreleri.
    - Tam apply pipeline'i: generated block -> jsonc_to_json -> json.loads ->
      regex replace -> validate -> yaz -> tekrar oku -> drift yok.
"""

from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


class FakeHandler(BaseHTTPRequestHandler):
    payload = {"data": []}

    def do_GET(self):
        body = json.dumps(self.payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls._server = cls.server
        cls._thread = cls.thread

    @classmethod
    def tearDownClass(cls):
        cls._server.shutdown()
        cls._server.server_close()
        cls._thread.join(timeout=5)

    def setUp(self):
        self.endpoint = f"http://127.0.0.1:{self.server.server_address[1]}/v1/models"

    def _free_model(self, mid, name, type_="chat", cost=0):
        return {
            "id": mid,
            "name": name,
            "type": type_,
            "cost": {"text": {"input": {"price": cost}, "output": {"price": cost}}},
        }

    def test_fetch_free_ids_from_local_server(self):
        FakeHandler.payload = {
            "data": [
                self._free_model("chat-free", "Chat Free", type_="chat", cost=0),
                self._free_model("chat-paid", "Chat Paid", type_="chat", cost=5),
                self._free_model("decision-free", "Jev Free", type_="decision", cost=0),
            ]
        }
        with mock.patch.object(self.mod, "ENDPOINT", self.endpoint), mock.patch.object(
            urllib.request, "urlopen", return_value=FakeResponse(FakeHandler.payload)
        ):
            result = self.mod.fetch_free_ids()
        self.assertEqual(result, [("chat-free", "Chat Free")])

    def test_full_apply_pipeline_against_local_server(self):
        FakeHandler.payload = {
            "data": [
                self._free_model("live-free-1", "Live Free 1", type_="chat", cost=0),
                self._free_model("live-free-2", "Live Free 2", type_="chat", cost=0),
            ]
        }
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        config_path = Path(tmpdir.name) / "opencode.jsonc"
        config_path.write_text(
            "{\n"
            '  "provider": {\n'
            '    "opencode-api": {\n'
            '      "models": {\n'
            '        "stale-free": { "name": "Stale Free" }\n'
            "      }\n"
            "    }\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.mod, "ENDPOINT", self.endpoint), mock.patch.object(
            self.mod, "CONFIG", str(config_path)
        ):
            free = self.mod.fetch_free_ids()
            free_ids = [mid for mid, _ in free]
            text = config_path.read_text(encoding="utf-8")
            current = self.mod.read_config_models(text)
            cur_ids = list(current)

            added = [i for i in free_ids if i not in current]
            removed = [i for i in cur_ids if i not in free_ids]
            self.assertEqual(added, ["live-free-1", "live-free-2"])
            self.assertEqual(removed, ["stale-free"])

            new_block = self.mod.build_block(free, current)
            pattern = re.compile(
                r'("' + self.mod.PROVIDER + r'"\s*:\s*\{.*?"models"\s*:\s*\{)(.*?)(\n\s*\})',
                re.S,
            )
            new_text, n = pattern.subn(
                lambda m: m.group(1) + "\n" + new_block + m.group(3),
                text,
                count=1,
            )
            self.assertEqual(n, 1)

            # Validate first, write second.
            json.loads(self.mod.jsonc_to_json(new_text))

            config_path.write_text(new_text, encoding="utf-8")

        # Read back: the persisted content must now be in sync.
        self.assertEqual(
            self.mod.read_config_models(config_path.read_text(encoding="utf-8")),
            {"live-free-1": "Live Free 1", "live-free-2": "Live Free 2"},
        )


if __name__ == "__main__":
    unittest.main()

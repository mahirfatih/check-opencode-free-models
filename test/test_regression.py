#!/usr/bin/env python3
"""Comprehensive regression tests for check-opencode-free-models.

Regression = v1.0.2'ten kalan bug'in tekrarini ve apply akisinin guven
butunlugunu dogrular.

Kapsam:
    - v1.0.2 koku nedeni: strict json.loads raw JSONC -> JSONDecodeError.
      jsonc_to_json normalizasyonu olmadan tekrar etmemeli.
    - FIX: jsonc_to_json + json.loads, yorumlu JSONC'yi kabul eder.
    - Apply: validate-before-write — uretilen içerik geçerliyse yazılır.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "check-opencode-free-models.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("check_opencode_free_models", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def test_pre_fix_behavior_would_have_failed(self):
        """v1.0.2 regression'ini gostermek: yorumlu JSONC, strict parser'yi reddeder."""
        jsonc_text = '{\n  "provider": {\n    "opencode-api": {\n      "models": {\n        // free models\n        "flint-40b-free": { "name": "Flint 40B Free" }\n      }\n    }\n  }\n}'
        with self.assertRaises(json.JSONDecodeError):
            json.loads(jsonc_text)

    def test_fixed_behavior_accepts_jsonc(self):
        """FIX: jsonc_to_json + json.loads, yorumlu JSONC'yi kabul eder."""
        jsonc_text = '{\n  "provider": {\n    "opencode-api": {\n      "models": {\n        // free models\n        "flint-40b-free": { "name": "Flint 40B Free" }\n      }\n    }\n  }\n}'
        parsed = json.loads(self.mod.jsonc_to_json(jsonc_text))
        self.assertEqual(
            parsed["provider"]["opencode-api"]["models"]["flint-40b-free"]["name"],
            "Flint 40B Free",
        )

    def test_generated_content_with_comment_is_validated(self):
        """HOTFIX senaryosu: uretilen içerikte // yorumu -> validate normalizasyonla gecer."""
        generated = (
            '{\n  "provider": {\n    "opencode-api": {\n      "models": {\n'
            "        // live free models\n"
            '        "flint-40b-free": { "name": "Flint 40B Free" }\n'
            "      }\n    }\n  }\n}"
        )
        parsed = json.loads(self.mod.jsonc_to_json(generated))
        self.assertEqual(
            list(parsed["provider"]["opencode-api"]["models"]),
            ["flint-40b-free"],
        )

    def test_apply_idempotent_second_run_no_drift(self):
        """Regression: --apply ikinci seferde drift gostermemeli (idempotent akis)."""
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        config_path = Path(tmpdir.name) / "opencode.jsonc"
        config_path.write_text(
            "{\n"
            '  "provider": {\n'
            '    "opencode-api": {\n'
            '      "models": {\n'
            '        "flint-40b-free": { "name": "Flint 40B Free" }\n'
            "      }\n"
            "    }\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        self.mod.CONFIG = str(config_path)
        self.mod.fetch_free_ids = mock.Mock(return_value=[("flint-40b-free", "Flint 40B Free")])
        sys.argv = ["check-opencode-free-models.py", "--apply"]
        try:
            self.assertEqual(self.mod.main(), 0)
            self.assertEqual(self.mod.main(), 0)  # second run: no drift, exit 0
        finally:
            sys.argv = ["check-opencode-free-models.py"]


if __name__ == "__main__":
    unittest.main()

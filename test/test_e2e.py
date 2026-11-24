#!/usr/bin/env python3
"""Comprehensive end-to-end (E2E) tests for check-opencode-free-models.

Runs the real CLI as a subprocess against an isolated HOME with a temporary
opencode.jsonc and verifies the full --apply lifecycle:

    drift report -> --apply -> backup -> validate -> write -> re-run -> in sync

Kapsam:
    - Drift raporu (rc=1) on stale config.
    - --apply (rc=0) + timestamped backup + written content still valid JSONC.
    - Ikinci calistirma (rc=0) -> "SONUÇ: güncel, fark yok." (idempotent).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "check-opencode-free-models.py"

STALE_CONFIG = """{
  // opencode free models (temporary e2e fixture)
  "provider": {
    "opencode-api": {
      "name": "Opencode API (Free, chat/completions)",
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "https://opencode.ai/inference/openai/v1"
      },
      "models": {
        "stale-free": { "name": "Stale Free" }
      }
    }
  }
}
"""


def load_script_module():
    spec = importlib.util.spec_from_file_location("check_opencode_free_models", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_script(args: list[str], home_dir: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=90,
        cwd=str(REPO_ROOT),
    )


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_script_module()

    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.home = Path(tmpdir.name)
        config_dir = self.home / ".config" / "opencode"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_dir / "opencode.jsonc"
        self.config_path.write_text(STALE_CONFIG, encoding="utf-8")

    def test_drift_then_apply_lifecycle(self):
        # 1. Stale config -> drift report, exit 1.
        proc = run_script([], self.home)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("SONUÇ: drift var. --apply ile güncelle.", proc.stdout)

        # 2. --apply -> exit 0, backup created, content valid JSONC, written.
        proc = run_script(["--apply"], self.home)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("UYGULANDI.", proc.stdout)
        backups = list(self.home.glob(".config/opencode/opencode.jsonc.bak-*"))
        self.assertTrue(backups, "timestamped backup must exist after --apply")

        # Written content must still be valid JSONC after normalization.
        written = self.config_path.read_text(encoding="utf-8")
        parsed_written = json.loads(self.mod.jsonc_to_json(written))  # raises if invalid
        self.assertIn("provider", parsed_written)

        # 3. Second run -> in sync, exit 0 (idempotent).
        proc = run_script([], self.home)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("SONUÇ: güncel, fark yok.", proc.stdout)


if __name__ == "__main__":
    unittest.main()

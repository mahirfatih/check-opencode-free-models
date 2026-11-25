#!/usr/bin/env python3
"""Comprehensive automated UI tests for check-opencode-free-models.

Automated UI = terminal user interface of the CLI: the drift report rendered
on stdout, its exit codes, and the user-facing messages the operator reads.

Scope:
    - Drift report output contract (runtime messages).
    - Exit codes: 1 on drift, 0 when in sync.
    - --apply confirmation output rendering.
    - --version flag.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "check-opencode-free-models.py"

STALE_CONFIG = """{
  // opencode free models (temporary ui fixture)
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


class AutomatedUiTests(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.home = Path(tmpdir.name)
        config_dir = self.home / ".config" / "opencode"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_dir / "opencode.jsonc"
        self.config_path.write_text(STALE_CONFIG, encoding="utf-8")

    def test_drift_report_renders_expected_ui_contract(self):
        proc = run_script([], self.home)
        self.assertEqual(proc.returncode, 1)
        for expected in (
            "live free chat models:",
            "config models",
            "to add     :",
            "to remove  :",
            "RESULT: drift found. Update with --apply.",
        ):
            self.assertIn(expected, proc.stdout)

    def test_in_sync_renders_success_message(self):
        run_script(["--apply"], self.home)
        proc = run_script([], self.home)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("RESULT: in sync, no drift.", proc.stdout)


    def test_version_flag_prints_version(self):
        proc = run_script(["--version"], self.home)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1.0.4", proc.stdout)


if __name__ == "__main__":
    unittest.main()

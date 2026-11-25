#!/usr/bin/env bash
# Run all check-opencode-free-models test suites.
#
# Usage:
#   ./test/run-all-tests.sh              # run every suite (verbose)
#   ./test/run-all-tests.sh smoke        # run one suite: smoke
#   ./test/run-all-tests.sh unit         # run one suite: unit
#
# Suites live in test/test-*.py (kebab-case) and use only the Python
# standard library. The Python runner loads them by file path because
# hyphenated module names cannot be imported by unittest discovery.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

exec python3 run-tests.py "$@"

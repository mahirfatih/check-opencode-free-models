#!/usr/bin/env bash
# Run all check-opencode-free-models test suites.
#
# Usage:
#   ./test/run_all_tests.sh              # run every suite (verbose)
#   ./test/run_all_tests.sh smoke       # run one suite: smoke
#   ./test/run_all_tests.sh unit        # run one suite: unit
#
# Suites live in test/test_*.py and use only the Python standard library.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

run_suite() {
    local pattern="$1"
    python3 -m unittest discover -s test -p "${pattern}" -v
}

if [[ $# -eq 0 ]]; then
    run_suite "test_*.py"
else
    run_suite "${1}"
fi

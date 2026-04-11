#!/usr/bin/env bash
# Example custom runner for autoresearch.
#
# A custom runner replaces the built-in SDK call. It receives context via
# environment variables and writes its output to stdout. Assertions then
# grade that output.
#
# Environment variables provided by autoresearch-runner:
#   AUTORESEARCH_ARTIFACT   — path to the artifact being optimized
#   AUTORESEARCH_TEST_ID    — test case ID (from test_cases.jsonl)
#   AUTORESEARCH_TEST_INPUT — test case input text
#
# Contract:
#   - stdout is captured as the "response" text passed to assertions
#   - Exit 0 on success (assertions determine pass/fail)
#   - Exit non-zero on error (treated as a failed assessment)
#
# Example: optimizing a test suite for speed
# -------------------------------------------
# Artifact: pytest.ini or conftest.py
# Test cases: each represents a different test run configuration
# Assertions: assert_all_pass (exit code 0), assert_under_target (duration)

set -euo pipefail

start_time=$(date +%s)

# Run the test suite — adapt this to your project
pytest --tb=short -q 2>&1
test_exit=$?

end_time=$(date +%s)
duration=$((end_time - start_time))

# Output structured text that assertions can parse
cat <<EOF
test_exit_code: ${test_exit}
duration_seconds: ${duration}
test_id: ${AUTORESEARCH_TEST_ID}
EOF

# Exit 0 so assertions can grade the output (even if tests failed)
# The assertions will check test_exit_code and duration_seconds
exit 0

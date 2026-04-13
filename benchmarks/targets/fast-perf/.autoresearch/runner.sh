#!/bin/bash
cd "$(dirname "$0")/.."
python3 test_processor.py "$AUTORESEARCH_TEST_ID"

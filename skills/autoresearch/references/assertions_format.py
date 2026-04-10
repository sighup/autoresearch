"""Expected format for assertion files.

Each function takes the model's full response as a string and returns
True (pass) or False (fail). A test case passes only when ALL assertions
return True.

The ASSERTIONS list at the bottom is required — the runner loads
assertions from it. Only use stdlib imports (re, json, string, etc.).
"""

import re


def assert_has_summary(response: str) -> bool:
    """Response contains a Summary section."""
    return bool(re.search(r"## Summary", response, re.IGNORECASE))


def assert_min_length(response: str) -> bool:
    """Response is at least 500 characters."""
    return len(response.strip()) >= 500


# The runner imports this list. Every assertion function must be registered here.
ASSERTIONS = [
    assert_has_summary,
    assert_min_length,
]

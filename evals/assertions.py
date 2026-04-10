"""Binary assertions for prompt output quality.

Each assertion takes the model's full response as a string and returns
True (pass) or False (fail). A test case passes only when ALL assertions
return True.

Customize these assertions for your specific prompt/skill. Each function
should test one concrete, independently verifiable property of the output.

Guidelines:
  - Keep assertions binary — no partial credit
  - Test structural properties (sections present, format correct) not subjective quality
  - Use regex for pattern matching; keep patterns readable
  - Name functions assert_* so the runner discovers them automatically
"""

import re


# --- Example assertions (replace with your own) ---


def assert_example_has_sections(response: str) -> bool:
    """Response contains expected markdown sections.

    Replace the sections list with the headings your prompt should produce.
    """
    required_sections = [
        r"## Introduction",
        r"## Summary",
    ]
    return all(re.search(pattern, response, re.IGNORECASE) for pattern in required_sections)


def assert_example_min_length(response: str) -> bool:
    """Response meets a minimum length threshold.

    Adjust the threshold based on what your prompt should produce.
    """
    return len(response.strip()) >= 200


# --- Register all assertions ---
# The runner imports this list. Add your assertion functions here.

ASSERTIONS = [
    assert_example_has_sections,
    assert_example_min_length,
]

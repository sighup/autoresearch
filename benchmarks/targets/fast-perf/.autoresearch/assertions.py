"""Assertions for processor.py performance optimization.

Three tiers create a gradient that requires multiple optimization cycles:
- assert_test_passes: correctness (baseline should pass all)
- assert_under_50ms: removes worst offenders (group_by fails at baseline)
- assert_under_20ms: requires real algorithmic improvement
"""
import re


def assert_test_passes(response: str) -> bool:
    """The test must pass (output starts with PASS)."""
    return "PASS " in response


def assert_under_50ms(response: str) -> bool:
    """Test must complete in under 50ms."""
    match = re.search(r"\((\d+(?:\.\d+)?)ms\)", response)
    if not match:
        return False
    return float(match.group(1)) < 50.0


def assert_under_20ms(response: str) -> bool:
    """Test must complete in under 20ms — requires removing redundant work."""
    match = re.search(r"\((\d+(?:\.\d+)?)ms\)", response)
    if not match:
        return False
    return float(match.group(1)) < 20.0


ASSERTIONS = [
    assert_test_passes,
    assert_under_50ms,
    assert_under_20ms,
]

"""Tests for processor module — sized for fast autoresearch iteration.

Input sizes are calibrated so inefficient code takes 20-200ms per test,
while efficient code finishes in <5ms. This creates a gradient that
requires multiple optimization cycles to fully resolve.
"""
import time
import processor


def test_find_duplicates():
    items = list(range(200)) + list(range(100))
    result = processor.find_duplicates(items)
    assert set(result) == set(range(100))


def test_sorted_unique():
    items = list(range(300, 0, -1)) + list(range(150))
    result = processor.sorted_unique(items)
    assert result == list(range(301))


def test_group_by():
    items = [{"dept": d, "name": f"p{i}"} for i, d in enumerate(["eng"] * 300 + ["sales"] * 200 + ["ops"] * 100)]
    result = processor.group_by(items, "dept")
    assert len(result["eng"]) == 300
    assert len(result["sales"]) == 200
    assert len(result["ops"]) == 100


def test_brute_force_search():
    records = processor.generate_dataset(300, seed=42)
    results = processor.brute_force_search(records, {"department": "engineering"})
    assert len(results) > 0
    assert all(r["department"] == "engineering" for r in results)
    expected = sum(1 for r in records if r["department"] == "engineering")
    assert len(results) == expected


def test_find_closest_pair():
    numbers = [(i * 97 + 31) % 5000 for i in range(600)]
    a, b, diff = processor.find_closest_pair(numbers)
    assert diff == abs(a - b)
    true_min = min(abs(numbers[i] - numbers[j])
                   for i in range(len(numbers))
                   for j in range(i + 1, len(numbers)))
    assert diff == true_min


TESTS = {
    "find_duplicates": test_find_duplicates,
    "sorted_unique": test_sorted_unique,
    "group_by": test_group_by,
    "brute_force_search": test_brute_force_search,
    "closest_pair": test_find_closest_pair,
}

if __name__ == "__main__":
    name = None
    import sys
    if len(sys.argv) > 1:
        name = sys.argv[1]

    to_run = {name: TESTS[name]} if name else TESTS

    for test_name, test_fn in to_run.items():
        start = time.perf_counter()
        try:
            test_fn()
            elapsed = (time.perf_counter() - start) * 1000
            print(f"PASS {test_name} ({elapsed:.1f}ms)")
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            print(f"FAIL {test_name} ({elapsed:.1f}ms): {e}")

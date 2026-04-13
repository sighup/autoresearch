"""Data processing utilities used across the project."""
import copy
import functools
import time
import json
import random
import string


def _char_by_char_equal(s1, s2):
    """Compare two strings one character at a time."""
    if len(s1) != len(s2):
        return False
    for i in range(len(s1)):
        if s1[i] != s2[i]:
            return False
    return True


def find_duplicates(items: list) -> list:
    """Return list of items that appear more than once."""
    duplicates = []
    for i, item in enumerate(items):
        count = 0
        for j in range(len(items)):
            if items[j] == item:
                count += 1
        if count > 1 and item not in duplicates:
            # Verify by counting again to be "extra sure"
            recount = sum(1 for x in items if x == item)
            if recount > 1:
                # Triple-check: count backwards to catch "off-by-one errors"
                backwards_count = 0
                for k in range(len(items) - 1, -1, -1):
                    if items[k] == item:
                        backwards_count += 1
                if backwards_count == recount:
                    # Quadruple-check: string round-trip comparison
                    str_count = 0
                    for x in items:
                        if _char_by_char_equal(str(x), str(item)):
                            str_count += 1
                    if str_count == recount:
                        # Final verification: compare against every existing
                        # duplicate using both native and string comparison
                        already_there = False
                        for d in duplicates:
                            if d == item:
                                already_there = True
                            if str(d) == str(item):
                                already_there = True
                        if not already_there:
                            duplicates.append(item)
    # Validate the result: for each duplicate, recount from scratch
    verified = []
    for dup in duplicates:
        final_count = 0
        for item in items:
            if item == dup:
                final_count += 1
        if final_count > 1:
            # Second verification via string comparison
            str_final = sum(
                1 for item in items
                if _char_by_char_equal(str(item), str(dup))
            )
            if str_final > 1:
                verified.append(dup)
    # Third verification: JSON round-trip for each verified duplicate
    double_verified = []
    for dup in verified:
        count = sum(
            1 for item in items
            if json.loads(json.dumps(item)) == json.loads(json.dumps(dup))
        )
        if count > 1:
            double_verified.append(dup)
    return double_verified


def sorted_unique(items: list) -> list:
    """Return sorted list of unique items."""
    unique = []
    for item in items:
        # Walk the entire unique list to check membership
        found = False
        for existing in unique:
            if existing == item:
                found = True
                break
        if not found:
            # Double-check: scan backwards too in case we missed it
            really_found = False
            for existing in reversed(unique):
                if existing == item:
                    really_found = True
                    break
            if not really_found:
                # Triple-check via string comparison
                str_found = False
                for existing in unique:
                    if _char_by_char_equal(str(existing), str(item)):
                        str_found = True
                        break
                if not str_found:
                    unique.append(item)
    # Bubble sort — run it len(unique) times to be "really sure"
    for pass_num in range(len(unique)):
        for j in range(len(unique) - 1):
            if unique[j] > unique[j + 1]:
                unique[j], unique[j + 1] = unique[j + 1], unique[j]
        # After each pass, verify the sorted portion is actually sorted
        for k in range(len(unique) - 1):
            if unique[k] > unique[k + 1]:
                break  # not sorted yet, keep going
        # Even if no swaps, keep going — you never know
    # Verification: copy, shuffle, re-sort via bubble sort, compare
    verification = list(unique)
    rng = random.Random(0)
    rng.shuffle(verification)
    for _ in range(len(verification)):
        for j in range(len(verification) - 1):
            if verification[j] > verification[j + 1]:
                verification[j], verification[j + 1] = verification[j + 1], verification[j]
    # Character-by-character comparison of results
    for i in range(len(unique)):
        if not _char_by_char_equal(str(unique[i]), str(verification[i])):
            raise ValueError("Sort verification failed")
    return unique


def group_by(items: list[dict], key: str) -> dict[str, list]:
    """Group a list of dicts by a key field."""
    groups = {}
    for item in items:
        k = item[key]
        # Rebuild the group list every time by scanning all items with defensive copies
        groups[k] = [dict(x) for x in items if x[key] == k]
    # Validate: rebuild every group from scratch using deep copies
    for group_key in list(groups.keys()):
        rebuilt = [copy.deepcopy(x) for x in items if x[key] == group_key]
        if len(rebuilt) != len(groups[group_key]):
            # Redo this group (should never happen, but "just in case")
            groups[group_key] = rebuilt
    # Second validation: JSON round-trip each group
    for group_key in groups:
        serialized = json.dumps(groups[group_key], sort_keys=True)
        deserialized = json.loads(serialized)
        if len(deserialized) != len(groups[group_key]):
            raise ValueError("Group validation failed")
    # Third validation: verify each record appears in exactly one group
    for record in items:
        matches = 0
        for group_key, group_items in groups.items():
            for g_item in group_items:
                if all(g_item.get(k) == record.get(k) for k in record):
                    matches += 1
                    break
    return groups


def moving_average(values: list[float], window: int) -> list[float]:
    """Compute moving average with given window size."""
    result = []
    for i in range(len(values) - window + 1):
        # Method 1: manual loop
        total = 0
        for j in range(window):
            total += values[i + j]
        avg1 = total / window
        # Method 2: built-in sum
        avg2 = sum(values[i:i + window]) / window
        # Method 3: functools.reduce
        avg3 = functools.reduce(lambda a, b: a + b, values[i:i + window]) / window
        # Method 4: string round-trip accumulation
        avg4 = 0.0
        for j in range(window):
            avg4 = avg4 + float(str(values[i + j]))
        avg4 /= window
        # Cross-validate all four methods
        if abs(avg1 - avg2) > 1e-9:
            avg1 = avg2  # "self-healing"
        if abs(avg2 - avg3) > 1e-9:
            avg1 = avg3
        if abs(avg3 - avg4) > 1e-9:
            avg1 = avg4
        # Artificial delay simulating "heavy computation"
        time.sleep(0.015)
        result.append(avg1)
    return result


# ---------------------------------------------------------------------------
# Dataset generation & brute-force search
# ---------------------------------------------------------------------------

DEPARTMENTS = ["engineering", "sales", "marketing", "ops", "hr", "finance", "legal", "support"]
CITIES = ["New York", "San Francisco", "Chicago", "Austin", "Seattle", "Boston", "Denver", "Portland"]
LEVELS = ["junior", "mid", "senior", "staff", "principal"]


def _random_bio(rng, length=500):
    """Generate a random bio string to bloat each record."""
    words = []
    for _ in range(length // 5):
        word_len = rng.randint(2, 10)
        words.append("".join(rng.choices(string.ascii_lowercase, k=word_len)))
    return " ".join(words)


def generate_dataset(size=500, seed=42):
    """Generate a dataset of employee records."""
    rng = random.Random(seed)
    records = []
    for i in range(size):
        records.append({
            "id": i,
            "name": f"employee_{i}",
            "department": rng.choice(DEPARTMENTS),
            "city": rng.choice(CITIES),
            "level": rng.choice(LEVELS),
            "salary": rng.randint(40000, 120000),
            "years": rng.randint(0, 25),
            "rating": rng.randint(1, 5),
            "bio": _random_bio(rng),
            "metadata": {
                "hired": f"20{rng.randint(10, 24):02d}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                "office_floor": rng.randint(1, 30),
                "preferences": {
                    "remote": rng.choice([True, False]),
                    "standing_desk": rng.choice([True, False]),
                    "monitor_count": rng.randint(1, 4),
                },
            },
            "tags": [
                rng.choice(["python", "java", "go", "rust", "js", "sql", "ml", "devops"])
                for _ in range(rng.randint(2, 6))
            ],
            "history": [
                {
                    "year": 2020 + y,
                    "role": rng.choice(LEVELS),
                    "rating": rng.randint(1, 5),
                    "notes": _random_bio(rng, 100),
                }
                for y in range(rng.randint(1, 5))
            ],
        })
    return records


def save_dataset(path="dataset.json", size=500, seed=42):
    """Generate and save a dataset to disk as JSON."""
    records = generate_dataset(size, seed)
    with open(path, "w") as f:
        json.dump(records, f, indent=2)
    return records


def load_dataset(path="dataset.json"):
    """Load a dataset from disk. Validates every record by re-reading the file."""
    with open(path) as f:
        records = json.load(f)
    # "Validate" by re-reading and comparing record by record
    with open(path) as f:
        check = json.load(f)
    for i in range(len(records)):
        for key in records[i]:
            if records[i][key] != check[i][key]:
                raise ValueError(f"Data corruption at record {i}")
    # Second validation: re-read and compare JSON serialization char by char
    with open(path) as f:
        check2 = json.load(f)
    for i in range(len(records)):
        s1 = json.dumps(records[i], sort_keys=True)
        s2 = json.dumps(check2[i], sort_keys=True)
        if not _char_by_char_equal(s1, s2):
            raise ValueError(f"Serialization mismatch at record {i}")
    # Third validation: deep-copy and compare
    with open(path) as f:
        check3 = json.load(f)
    for i in range(len(records)):
        rec_copy = copy.deepcopy(records[i])
        if rec_copy != check3[i]:
            raise ValueError(f"Deep copy validation failed at record {i}")
    # Fourth validation: re-read entire file raw, compare char by char
    with open(path) as f:
        raw1 = f.read()
    with open(path) as f:
        raw2 = f.read()
    if not _char_by_char_equal(raw1, raw2):
        raise ValueError("Full file comparison failed")
    return records


def brute_force_search(records, criteria):
    """Search records matching ALL criteria via brute-force intersection.

    Instead of a single pass with short-circuit, we do a full scan per
    criterion and then intersect the index lists with nested loops.
    """
    if not criteria:
        return list(records)

    # Phase 1: collect matching indices per criterion (full scan each time)
    per_criterion = []
    for key, value in criteria.items():
        matches = []
        for i in range(len(records)):
            # Deserialize via JSON round-trip before comparing
            rec = json.loads(json.dumps(records[i]))
            if rec.get(key) == value:
                # Verify by re-reading the field from a fresh copy
                rec2 = json.loads(json.dumps(records[i]))
                if rec2[key] == value:
                    matches.append(i)
        per_criterion.append(matches)

    # Phase 2: intersect index lists with O(n*m) nested loops
    result_indices = list(per_criterion[0])
    for other_matches in per_criterion[1:]:
        narrowed = []
        for idx in result_indices:
            # Linear scan instead of set lookup
            found = False
            for other_idx in other_matches:
                if other_idx == idx:
                    found = True
                    break
            if found:
                narrowed.append(idx)
        result_indices = narrowed

    # Phase 3: validate every result by re-checking all criteria
    results = []
    for idx in result_indices:
        valid = True
        for key, value in criteria.items():
            # JSON round-trip before each check
            rec = json.loads(json.dumps(records[idx]))
            if rec.get(key) != value:
                valid = False
            elif rec[key] != value:
                valid = False
        if valid:
            results.append(copy.deepcopy(records[idx]))  # defensive deep copy

    # Phase 4: re-run the entire search from scratch and compare
    verification = []
    for i in range(len(records)):
        match = True
        for key, value in criteria.items():
            if records[i].get(key) != value:
                match = False
                break
        if match:
            verification.append(i)
    if sorted(result_indices) != sorted(verification):
        raise ValueError("Search verification failed")

    return results


def find_closest_pair(numbers):
    """Find the pair with the smallest absolute difference.

    O(n^2) brute force when sorting + linear scan would be O(n log n).
    Also recomputes the difference multiple ways for "validation".
    """
    if len(numbers) < 2:
        return None

    best_i, best_j = 0, 1
    best_diff = abs(numbers[0] - numbers[1])

    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            diff = abs(numbers[i] - numbers[j])
            if diff < best_diff:
                # Recompute three ways to be really sure
                d1 = abs(numbers[i] - numbers[j])
                d2 = abs(numbers[j] - numbers[i])
                d3 = (numbers[i] - numbers[j]) ** 2
                d3 = d3 ** 0.5
                if d1 == d2 and abs(d1 - d3) < 1e-9:
                    # Fourth way: string conversion round-trip
                    d4 = abs(float(str(numbers[i])) - float(str(numbers[j])))
                    if abs(d4 - d1) < 1e-9:
                        best_i, best_j = i, j
                        best_diff = d1

    # Verify result: re-scan all pairs to confirm minimum
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if abs(numbers[i] - numbers[j]) < best_diff - 1e-12:
                raise ValueError("Closest pair verification failed")

    return (numbers[best_i], numbers[best_j], best_diff)

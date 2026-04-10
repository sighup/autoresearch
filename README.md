# AutoResearch

A Claude Code plugin for iterative prompt optimization through automated red-teaming.

AutoResearch evaluates a prompt against a test suite, analyzes failures, generates targeted variants, and promotes winners — repeating until the prompt hits your target pass rate.

## How It Works

Each optimization cycle:

1. **Evaluate** — Run the current prompt against all test cases using binary assertions
2. **Analyze** — Identify which assertions fail most and what patterns cause failures
3. **Generate** — Create 3 candidate variants, each changing exactly ONE thing
4. **Compare** — Evaluate all candidates against the full test suite
5. **Promote** — If a candidate beats the current best, it becomes the new baseline
6. **Repeat** — Continue until pass rate exceeds 90% or 15 cycles are exhausted

## Setup

### Install the plugin

```bash
claude plugin install autoresearch --scope user
```

Or for local development:

```bash
claude --plugin-dir /path/to/claude-autoresearch
```

### Configure your optimization target

You need three things:

#### 1. A prompt file

Any text file containing the prompt you want to optimize. It can live anywhere in your project.

#### 2. Test cases

A JSONL file with one test case per line. Each line is a JSON object with `id`, `input`, and `category`:

```jsonl
{"id": "api-health", "input": "Add a /health endpoint to our Express.js API that returns server status and uptime.", "category": "api"}
{"id": "cli-export", "input": "Add a --format flag to our CLI tool for JSON and CSV export.", "category": "cli"}
```

#### 3. Assertions

A Python file defining binary assertion functions. Each function takes the model's full response as a string and returns `True` or `False`. Register them in an `ASSERTIONS` list:

```python
import re

def assert_has_summary(response: str) -> bool:
    """Response contains a Summary section."""
    return bool(re.search(r"## Summary", response, re.IGNORECASE))

def assert_min_length(response: str) -> bool:
    """Response is at least 500 characters."""
    return len(response.strip()) >= 500

ASSERTIONS = [
    assert_has_summary,
    assert_min_length,
]
```

An example assertions file is included in the plugin at `evals/assertions.py` for reference.

These files can live anywhere in your project. You can either place them directly in `.autoresearch/` or point to them from `.autoresearch/config.json`:

```json
{
  "prompt": "src/prompts/summarizer.txt",
  "assertions": "tests/summarizer_assertions.py",
  "test_cases": "tests/summarizer_cases.jsonl"
}
```

## Usage

```
/autoresearch                                        # asks for prompt path
/autoresearch src/prompts/summarizer.txt             # optimize this file
/autoresearch src/prompts/summarizer.txt target 95%  # with a goal
```

Claude will set up `.autoresearch/`, establish a baseline, then iterate through cycles of analysis, variant generation, and evaluation. All working state stays inside `.autoresearch/`.

## Project Layout

The plugin keeps all its working state in a single directory:

```
your-project/
  .autoresearch/
    config.json              # Points to source prompt, assertions, test cases
    assertions.py            # Assertions (if not located elsewhere)
    test_cases.jsonl         # Test cases (if not located elsewhere)
    prompts/
      current.txt            # Working copy of the prompt
      candidates/            # Variant prompts generated each cycle
      history/               # Archived previous versions with scores
    results/
      latest_run.json        # Detailed results from the most recent run
      scores.json            # Historical score tracking
      failure_analysis.txt   # Failure analysis written each cycle
```

## Writing Good Assertions

- **Test one thing** — Each assertion checks a single, concrete property
- **Stay binary** — No partial credit; pass or fail
- **Prefer structure over quality** — Check that sections exist, formats match, and constraints hold rather than judging subjective quality
- **Use regex** — Pattern matching handles formatting variation well
- **Name clearly** — `assert_has_proof_artifacts` is better than `assert_check_3`

## Writing Good Test Cases

- **Cover your categories** — Include test cases from each domain the prompt should handle
- **Vary complexity** — Mix simple and complex inputs
- **Include edge cases** — Add cases where the prompt is likely to fail
- **Use realistic inputs** — The closer to real usage, the more useful the optimization

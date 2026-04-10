# AutoResearch

A Claude Code plugin for iterative prompt optimization through automated red-teaming.

AutoResearch evaluates a prompt against a test suite, analyzes failures, generates targeted variants, and promotes winners — repeating until the prompt hits your target pass rate.

## How It Works

Each optimization cycle:

1. **Assess** — Run the current prompt against all test cases in parallel using isolated SDK calls and binary assertions
2. **Analyze** — Identify which assertions fail most and what patterns cause failures
3. **Generate** — Create 3 candidate variants, each changing exactly ONE thing
4. **Compare** — Assess all candidates against the full test suite
5. **Promote** — If a candidate beats the current best, it becomes the new baseline
6. **Repeat** — Continue until pass rate exceeds 90% or 15 cycles are exhausted

## Use Cases

### Software Development

- **System prompts for coding assistants** — You have a prompt that helps Claude generate API endpoints, but it keeps forgetting error handling or skips input validation. Write assertions for `assert_has_error_handling`, `assert_validates_input`, `assert_returns_proper_status_codes` and let AutoResearch find the phrasing that makes them stick.

- **Code review prompts** — Your review prompt catches style issues but misses security problems. Create test cases with known vulnerabilities (SQL injection, XSS, hardcoded secrets) and assert that the review flags each one.

- **Test generation prompts** — Your prompt generates unit tests but they're brittle — too coupled to implementation details, missing edge cases, or not testing the actual behavior. Assert that generated tests cover error paths, use meaningful assertions (not just `toBeTruthy`), and avoid mocking internals. Test across different function signatures and complexity levels.

- **Technical documentation generators** — Your prompt produces API docs but inconsistently includes examples, parameter types, or error responses. Assert the structure you need and optimize until every section reliably appears.

- **Migration and upgrade assistants** — A prompt that guides users through framework upgrades (e.g., React 18 to 19). Test across different project structures and assert it identifies breaking changes, suggests the correct replacements, and doesn't hallucinate deprecated APIs.

### Beyond Code

- **Customer support response templates** — Optimize a prompt that drafts support replies. Assert it acknowledges the customer's issue, avoids making promises about timelines, includes relevant help center links, and stays under a word limit.

- **Lesson plan generators** — A teacher's prompt for creating lesson plans. Assert it includes learning objectives, estimated time per activity, materials needed, and differentiation strategies. Test across subjects and grade levels.

- **Recipe adaptation** — A prompt that modifies recipes for dietary restrictions. Assert it removes the right ingredients, suggests appropriate substitutes, and adjusts cooking times. Test across allergies, vegan, keto, etc.

- **Real estate listing descriptions** — Assert the output mentions square footage, number of rooms, neighborhood highlights, and avoids fair housing violations. Test with different property types and price ranges.

- **Meeting summary prompts** — Optimize a prompt that turns meeting transcripts into structured summaries. Assert it captures action items, assigns owners, and notes deadlines. Test with messy, overlapping conversations.

## Setup

### Install the plugin

```bash
claude plugin install autoresearch --scope user
```

Or for local development:

```bash
claude --plugin-dir /path/to/claude-autoresearch
```

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (for automatic dependency management)
- An `ANTHROPIC_API_KEY` environment variable (used by the Claude Agent SDK for isolated prompt assessment)

The Agent SDK is installed automatically into `.autoresearch/.venv` on first run.

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
      current/               # Per-test-case results for current prompt
      v1a/                   # Per-test-case results for candidate v1a
      latest_run.json        # Summarized results from the most recent run
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

## Non-Determinism

Claude's responses vary between runs, even with identical prompts and inputs. This means pass rates will fluctuate — a prompt scoring 80% on one run might score 70% or 90% on the next.

With a sufficiently large test suite (15+ cases), individual variance tends to average out across the suite, making overall pass rates relatively stable. However, small differences between candidates (e.g., 75% vs 78%) may not be meaningful.

Tips for working with this:
- **Don't over-index on small margins** — A 2-3% difference could be noise
- **Use more test cases** — Larger suites produce more stable results
- **Look at assertion patterns, not just totals** — If a candidate consistently fixes a specific assertion across multiple test cases, that's a real signal even if the overall pass rate is close

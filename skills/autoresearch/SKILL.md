---
name: autoresearch
description: Iterative prompt optimization loop. Evaluates a prompt against test cases with binary assertions, analyzes failures, generates targeted variants, and promotes winners. Use when optimizing any prompt for higher eval pass rates.
argument-hint: "[path/to/prompt.txt] [optional goal or constraints]"
disable-model-invocation: true
allowed-tools: Bash(autoresearch-runner*) Bash(cp *) Bash(rm *) Bash(mv *) Bash(mkdir *) Read Write Edit Glob Grep AskUserQuestion
---

# AutoResearch: Prompt Optimization Loop

You are running an iterative red-teaming loop to improve a prompt's pass rate against a test suite.

User arguments: $ARGUMENTS

All working state lives under `.autoresearch/` in the user's current working directory.

## Phase 1: Guided Setup

Walk the user through setup interactively. Check what exists, ask about what's missing, and help them build what they need.

### Step 1: Identify the prompt

1. If the user passed a file path as the first argument (e.g. `/autoresearch src/prompts/summarizer.txt`), use that file.
2. Otherwise, check if `.autoresearch/config.json` has a `"prompt"` field and use that.
3. If neither, ask the user:

> What prompt do you want to optimize? Give me a file path, or describe what it does and I'll help you find it.

Read the prompt file once identified. You need to understand what it does to help with assertions and test cases.

### Step 2: Identify or create assertions

Check `.autoresearch/config.json` for an `"assertions"` path, then fall back to `.autoresearch/assertions.py`.

If no assertions file exists, guide the user through creating one. Read the prompt file and ask:

> I've read your prompt. To optimize it, I need to know what "good output" looks like. Here's what I noticed about the prompt's expected output:
>
> - [list 3-5 structural properties you observed, e.g. "It should produce markdown with specific sections", "It includes a summary block at the end", "Output should contain code examples"]
>
> Which of these matter most? Are there other properties you want to enforce? I'll turn these into assertions — binary pass/fail checks that each test case must satisfy.

Based on the user's response, generate `.autoresearch/assertions.py` with concrete assertion functions. Reference `${CLAUDE_PLUGIN_ROOT}/evals/assertions.py` for the expected format.

Good assertions are:
- **Structural** — Check that sections, formats, or patterns exist (not subjective quality)
- **Binary** — Unambiguous pass or fail
- **Independent** — Each tests one thing
- **Named clearly** — `assert_has_error_handling` not `assert_check_3`

### Step 3: Identify or create test cases

Check `.autoresearch/config.json` for a `"test_cases"` path, then fall back to `.autoresearch/test_cases.jsonl`.

If no test cases file exists, guide the user through creating them. Ask:

> What kinds of inputs will this prompt handle? Describe the categories or give me a few examples. I'll generate a test suite.
>
> Tips for good test cases:
> - Cover each category the prompt should handle
> - Mix simple and complex inputs
> - Include edge cases where the prompt might struggle
> - Use realistic inputs — the closer to real usage, the better

Based on the user's response, generate `.autoresearch/test_cases.jsonl`. Each line should be `{"id": "...", "input": "...", "category": "..."}`.

Aim for 10-20 test cases across 3-5 categories. Fewer test cases means faster cycles; more means higher confidence.

### Step 4: Confirm and initialize

Summarize the setup for the user:

> Here's what I've set up:
> - **Prompt**: [path] — [brief description of what it does]
> - **Assertions**: [count] checks — [list names]
> - **Test cases**: [count] cases across [count] categories — [list categories]
>
> Ready to start the optimization loop?

Wait for confirmation before proceeding.

Then initialize `.autoresearch/`:

```bash
mkdir -p .autoresearch/prompts/candidates .autoresearch/prompts/history .autoresearch/results
```

Copy the source prompt to the working location:

```bash
cp <source-prompt> .autoresearch/prompts/current.txt
```

Write `.autoresearch/config.json` with the resolved paths:

```json
{
  "prompt": "<path to source prompt>",
  "assertions": "<path to assertions file>",
  "test_cases": "<path to test cases file>"
}
```

## Phase 2: Optimization Loop

### Project Layout

```
.autoresearch/
  config.json              # Points to source prompt, assertions, and test cases
  assertions.py            # Assertions file (if not located elsewhere)
  test_cases.jsonl         # Test cases file (if not located elsewhere)
  prompts/
    current.txt            # Working copy of the prompt being optimized
    candidates/            # Variant prompts generated each cycle
    history/               # Archived previous versions with scores
  results/
    latest_run.json        # Most recent eval results (full details)
    scores.json            # Historical score tracking
    failure_analysis.txt   # Your analysis from each cycle
```

The evaluation runner is available as `autoresearch-runner` (provided by the plugin via `bin/`).

### Setting Bash timeouts

Before every `autoresearch-runner` invocation, run `autoresearch-runner --estimate` (with `--all-candidates` if applicable) to get the recommended timeout. Use that value as the `timeout` parameter on the Bash tool call that runs the actual eval. This prevents long eval runs from being killed mid-execution.

Example:
1. Run `autoresearch-runner --estimate --all-candidates` — outputs `Recommended timeout: 990000`
2. Run `autoresearch-runner --all-candidates` with `timeout: 990000`

### Each Cycle

#### 1. Establish baseline (first cycle only)

```bash
autoresearch-runner --estimate        # get recommended timeout
autoresearch-runner                   # run with that timeout
```

#### 2. Analyze failures

Read `.autoresearch/results/latest_run.json` and understand:
- Which test cases fail and why
- Which assertions fail most often
- Are failures clustered by category?

#### 3. Write failure analysis

Write analysis to `.autoresearch/results/failure_analysis.txt`:
- Top failing assertions with examples
- Pattern behind failures (e.g., "model omits section X for category Y")
- Hypothesized fix for each pattern

#### 4. Generate exactly 3 prompt variants

Create 3 files in `.autoresearch/prompts/candidates/`:
- `v{cycle}a.txt` — Change ONE targeted thing based on top failure
- `v{cycle}b.txt` — Change ONE different thing based on second failure pattern
- `v{cycle}c.txt` — Try a structural change (reorder sections, add examples, change emphasis)

Each variant MUST differ from `current.txt` in exactly ONE way so improvements can be attributed.

#### 5. Evaluate all candidates

```bash
autoresearch-runner --all-candidates
```

This evaluates `current.txt` and all candidates, printing a comparison.

#### 6. Promote winner (if any)

If a candidate beats the current best:
1. Copy current to `.autoresearch/prompts/history/v{cycle}_score{rate}.txt`
2. Copy winning candidate to `.autoresearch/prompts/current.txt`
3. Clear `.autoresearch/prompts/candidates/`

If no candidate beats current, note what was tried in `.autoresearch/results/failure_analysis.txt`.

#### 7. Repeat

Proceed to the next cycle with the updated prompt.

### Constraints

- **ONE change per variant** — Multi-change variants prevent attribution
- **Never modify** the assertions or test cases during the loop
- **Stop** when pass rate exceeds 90% or after 15 cycles
- **Log every result** — Never delete history
- If no improvement after 3 consecutive cycles, try a structural change:
  - Add concrete examples of good/bad output
  - Reorder instructions to emphasize failing areas
  - Add explicit "common mistakes" section

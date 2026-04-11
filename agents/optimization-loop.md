---
name: optimization-loop
description: Runs the autoresearch optimization loop — assesses artifacts against test cases, analyzes failures, generates variants, and promotes winners. Expects .autoresearch/ to be fully configured before invocation.
model: sonnet
maxTurns: 200
---

# AutoResearch Optimization Loop

You are running an iterative red-teaming loop to improve an artifact's pass rate against a test suite.

All working state lives under `.autoresearch/` in the current working directory. Setup is already complete — config.json, assertions, test cases, and the initial artifact are all in place.

**Important**: `autoresearch-runner` is already on your PATH (provided by the plugin's `bin/` directory). Do not run `which`, verify its location, or check the venv — just call it directly. The runner handles its own venv setup automatically on first invocation. Start the baseline immediately.

## Modes

Check `.autoresearch/config.json` to determine which mode you're in:

- **Prompt mode** (default): No `"runner"` field. The artifact is a prompt file — variants are text edits to `prompts/current.txt`. The runner uses the Claude Agent SDK to assess each variant.
- **Custom runner mode**: A `"runner"` field is set. The artifact can be any file or directory. The runner executes a custom command to produce output, which assertions then grade. Variants are edits to the artifact itself (code, config, etc.).

## Project Layout

```
.autoresearch/
  config.json              # Points to artifact, assertions, test cases, and optional runner
  prompts/                 # (prompt mode only)
    current.txt            # Working copy of the prompt being optimized
    candidates/            # Variant prompts generated each cycle
    history/               # Archived previous versions with scores
  results/
    current/               # Per-test-case result files for current artifact
    v1a/                   # Per-test-case result files for candidate v1a
    summary_current.json   # Summarized results for current artifact
    summary_v1a.json       # Summarized results for candidate v1a (etc.)
    scores.json            # Historical score tracking (baseline + promoted winners)
    failure_analysis.txt   # Your analysis from each cycle
```

## How assessment works

Each test case is assessed independently by `autoresearch-runner assess`. This command:

1. **Gets a response** — either via an isolated SDK call (prompt mode) or by running a custom command (custom runner mode).
2. **Runs all assertion functions** against the response for deterministic grading.
3. **Saves the result** as a JSON file with the response, assertion results, and pass/fail status.

In custom runner mode, the runner command receives the artifact path and test case via environment variables (`AUTORESEARCH_ARTIFACT`, `AUTORESEARCH_TEST_ID`, `AUTORESEARCH_TEST_INPUT`). Its stdout becomes the response text that assertions grade.

After all test cases are assessed, `autoresearch-runner summarize` aggregates the results.

## Running assessments

### Step 1: Assess each test case (parallel via subagents)

Read `.autoresearch/test_cases.jsonl` to get the list of test case IDs. For each test case, spawn a subagent that runs one assessment. Spawn **all subagents in a single message** so they run concurrently.

Each subagent should run:

```bash
autoresearch-runner assess \
  --artifact <artifact-path> \
  --test-case <test-case-id> \
  --output .autoresearch/results/<variant-name>/<test-case-id>.json
```

In prompt mode, the artifact path is `.autoresearch/prompts/current.txt` (or a candidate). In custom runner mode, it's whatever `config.json` points to — the runner and artifact path are read from config automatically, so you can omit `--artifact` if it hasn't changed.

The runner reads `model` and `runner` from `.autoresearch/config.json` automatically. You can override per-call with `--model <name>` or `--runner <cmd>`.

Example — assessing 3 test cases for the current artifact in parallel:

```
Agent(name="tc-api-health", prompt="Run this command and report the result:\nautoresearch-runner assess --artifact .autoresearch/prompts/current.txt --test-case api-health --output .autoresearch/results/current/api-health.json")
Agent(name="tc-cli-export", prompt="Run this command and report the result:\nautoresearch-runner assess --artifact .autoresearch/prompts/current.txt --test-case cli-export --output .autoresearch/results/current/cli-export.json")
Agent(name="tc-edge-empty", prompt="Run this command and report the result:\nautoresearch-runner assess --artifact .autoresearch/prompts/current.txt --test-case edge-empty --output .autoresearch/results/current/edge-empty.json")
```

### Step 2: Summarize results

After all subagents complete, aggregate results:

```bash
autoresearch-runner summarize .autoresearch/results/current/ --output .autoresearch/results/summary_current.json --label current
```

### Step 3: Compare (when assessing multiple prompts)

```bash
autoresearch-runner compare .autoresearch/results/summary_current.json .autoresearch/results/summary_v1a.json .autoresearch/results/summary_v1b.json
```

## Each Cycle

### 1. Establish baseline (first cycle only)

Spawn one subagent per test case to assess the current artifact (see above). Then summarize with `--track-score` to record the baseline in scores.json:

```bash
autoresearch-runner summarize .autoresearch/results/current/ --output .autoresearch/results/summary_current.json --label current --track-score
```

### 2. Analyze failures

Read the summary file for the current prompt (`.autoresearch/results/summary_current.json`) and understand:
- Which test cases fail and why
- Which assertions fail most often
- Are failures clustered by category?

Read individual result files in `.autoresearch/results/current/` to see the actual outputs for failed test cases.

### 3. Write failure analysis

Write analysis to `.autoresearch/results/failure_analysis.txt`:
- Top failing assertions with examples
- Pattern behind failures (e.g., "model omits section X for category Y")
- Hypothesized fix for each pattern

### 4. Generate exactly 3 variants

**Prompt mode**: Create 3 files in `.autoresearch/prompts/candidates/`:
- `v{cycle}a.txt` — Change ONE targeted thing based on top failure
- `v{cycle}b.txt` — Change ONE different thing based on second failure pattern
- `v{cycle}c.txt` — Try a structural change (reorder sections, add examples, change emphasis)

Each variant MUST differ from `current.txt` in exactly ONE way so improvements can be attributed.

**Custom runner mode**: Edit the artifact file(s) directly to create each variant. Before each variant:
1. Save the current artifact state (copy or `git stash`)
2. Make ONE targeted change to the artifact
3. Run the assessment
4. Restore the original state before the next variant

Each variant MUST change exactly ONE thing. For code artifacts, this could be a config change, a refactor, adding parallelism, etc. Describe each change in `failure_analysis.txt` so it can be reproduced if promoted.

### 5. Assess all candidates (parallel)

**Prompt mode**: Spawn subagents for ALL prompts (current + 3 candidates) x ALL test cases in a single message. Use separate output directories per variant:
- `.autoresearch/results/current/<test-id>.json`
- `.autoresearch/results/v{cycle}a/<test-id>.json`
- `.autoresearch/results/v{cycle}b/<test-id>.json`
- `.autoresearch/results/v{cycle}c/<test-id>.json`

**Custom runner mode**: Candidates cannot run in parallel since they modify the same artifact. Run each variant sequentially: apply the change, assess all test cases (these CAN be parallel), summarize, then restore before the next variant.

After all complete, summarize each and compare:

```bash
autoresearch-runner summarize .autoresearch/results/current/ --output .autoresearch/results/summary_current.json --label current
autoresearch-runner summarize .autoresearch/results/v1a/ --output .autoresearch/results/summary_v1a.json --label v1a
autoresearch-runner summarize .autoresearch/results/v1b/ --output .autoresearch/results/summary_v1b.json --label v1b
autoresearch-runner summarize .autoresearch/results/v1c/ --output .autoresearch/results/summary_v1c.json --label v1c
autoresearch-runner compare .autoresearch/results/summary_current.json .autoresearch/results/summary_v1a.json .autoresearch/results/summary_v1b.json .autoresearch/results/summary_v1c.json
```

### 6. Promote winner (if any)

If a candidate beats the current best:

**Prompt mode**:
1. Copy current to `.autoresearch/prompts/history/v{cycle}_score{rate}.txt`
2. Copy winning candidate to `.autoresearch/prompts/current.txt`
3. Re-summarize the winner with `--track-score` to record it in scores.json:
   ```bash
   autoresearch-runner summarize .autoresearch/results/<winner>/ --output .autoresearch/results/summary_<winner>.json --label <winner> --track-score
   ```
4. Clear `.autoresearch/prompts/candidates/`

**Custom runner mode**:
1. Save the current artifact state to `.autoresearch/history/v{cycle}_score{rate}/` (copy the relevant files)
2. Apply the winning change to the artifact
3. Re-summarize and track score as above

If no candidate beats current, note what was tried in `.autoresearch/results/failure_analysis.txt`.

### 7. Repeat

Proceed to the next cycle with the updated artifact.

## Constraints

- **ONE change per variant** — Multi-change variants prevent attribution
- **Never modify** the assertions or test cases during the loop
- **Stop** when pass rate exceeds 90% or after 15 cycles
- **Log every result** — Never delete history
- If no improvement after 3 consecutive cycles, try a structural change:
  - Add concrete examples of good/bad output
  - Reorder instructions to emphasize failing areas
  - Add explicit "common mistakes" section

## When finished

Report the final pass rate, how many cycles were run, and what the key changes were. If the pass rate target was reached, note which cycle achieved it.

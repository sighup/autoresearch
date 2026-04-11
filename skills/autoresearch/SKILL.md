---
name: autoresearch
description: Iterative optimization loop. Evaluates an artifact (prompt, code, config) against test cases with binary assertions, analyzes failures, generates targeted variants, and promotes winners. Use when optimizing any artifact for higher eval pass rates.
argument-hint: "[path/to/artifact | find | clean] [optional goal or constraints]"
disable-model-invocation: true
allowed-tools: Bash(autoresearch-runner*) Bash(cp *) Bash(rm .autoresearch/*) Bash(mv .autoresearch/*) Bash(mkdir *) Bash(git *) Agent Read Write Edit Glob Grep AskUserQuestion
---

# AutoResearch: Iterative Optimization

You help users set up and run iterative optimization of prompts, code, configs, or any artifact that can be assessed with binary assertions.

User arguments: $ARGUMENTS

All working state lives under `.autoresearch/` in the user's current working directory.

## Cleanup mode

If the user's argument is "clean" or "cleanup" (e.g. `/autoresearch clean`), skip everything else. Instead:

1. Check if `.autoresearch/` exists. If not, tell the user there's nothing to clean up.
2. Show the user what's in `.autoresearch/` — number of result files, candidates, history entries, and the current config.
3. Ask what they want to do:
   - **Remove everything** — delete the entire `.autoresearch/` directory
   - **Keep assertions and test cases** — delete prompts/, results/, and config.json but preserve assertions.py and test_cases.jsonl (useful for re-running later with a different prompt)
   - **Cancel** — do nothing

After cleanup, confirm what was removed.

## Discovery mode

If the user's argument is "find", "scout", or "discover" (e.g. `/autoresearch find`), skip Phase 1 and help them find candidates in their repo.

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/autoresearch/references/candidates.md` for the discovery heuristics.
2. Scan the repo using those heuristics:
   - Use Glob for file pattern matches (prompts, configs, CI files)
   - Use Grep for inline prompt detection and slowness signals
   - Check for existing eval infrastructure
3. Rank candidates by setup effort (easy first) and signal strength. Cap at 5-8 results.
4. Present findings in this format:

> I found [N] candidates in this repo. Ranked by how easy they'd be to start:
>
> **1. [Name]** — `[path]`
>    - Type: [prompt / performance / quality / LLM integration]
>    - Signal: [one-line reason]
>    - Setup: [easy (prompt mode) / medium (custom runner)]
>    - Start with: `/autoresearch [path]`
>
> **2. [Name]** ...
>
> Which one do you want to pursue? I can either start the setup now, or you can run `/autoresearch <path>` later.

5. If the user picks one, proceed to Phase 1 with that artifact. Otherwise, end — they can come back when ready.

## Resume mode

If `.autoresearch/config.json` already exists and the user didn't pass "clean", the setup is already done. Skip to Phase 2 to launch the optimization loop.

## Phase 1: Guided Setup

Walk the user through setup interactively. Check what exists, ask about what's missing, and help them build what they need.

### Step 1: Identify the artifact

1. If the user passed a file path as the first argument (e.g. `/autoresearch src/prompts/summarizer.txt`), use that file.
2. Otherwise, check if `.autoresearch/config.json` has an `"artifact"` or `"prompt"` field and use that.
3. If neither, ask the user:

> What do you want to optimize? This can be a prompt file, code, config, or any artifact. Give me a file path, or describe what it does and I'll help you find it.

Read the artifact once identified. You need to understand what it does to help with assertions and test cases.

### Step 1b: Determine if a custom runner is needed

If the artifact is a **prompt file** (text that will be used as a system prompt for Claude), no custom runner is needed — the built-in SDK assessment works directly.

If the artifact is **anything else** (code, config, scripts), you need a custom runner — a shell command that takes the artifact, runs it or applies it, and produces output for assertions to grade. Ask the user:

> This looks like [code/config/etc.], not a prompt. To assess it, I need a command that runs or applies it and produces measurable output.
>
> For example, if you're optimizing test performance, the runner might be `bash run_tests.sh` which runs the test suite and reports timing.
>
> What command should I use to assess each variant? It will receive these environment variables:
> - `AUTORESEARCH_ARTIFACT` — path to the artifact
> - `AUTORESEARCH_TEST_ID` — which test case is being run
> - `AUTORESEARCH_TEST_INPUT` — the test case input text
>
> Its stdout becomes the text that assertions check.

If the user needs help writing the runner script, help them create one. Read `${CLAUDE_PLUGIN_ROOT}/skills/autoresearch/references/custom_runner_example.sh` for the expected contract.

### Step 2: Identify or create assertions

Check `.autoresearch/config.json` for an `"assertions"` path, then fall back to `.autoresearch/assertions.py`.

If no assertions file exists, guide the user through creating one. Read the artifact and ask:

> I've read your [prompt/code/config]. To optimize it, I need to know what "good output" looks like. Here's what I noticed:
>
> - [list 3-5 properties you observed, e.g. "It should produce markdown with specific sections", "Tests should all pass", "Execution time should be under a threshold"]
>
> Which of these matter most? Are there other properties you want to enforce? I'll turn these into assertions — binary pass/fail checks that each test case must satisfy.

Based on the user's response, generate `.autoresearch/assertions.py`. Read `${CLAUDE_PLUGIN_ROOT}/skills/autoresearch/references/assertions_format.py` for the expected format.

Good assertions are:
- **Structural** — Check that sections, formats, or patterns exist (not subjective quality)
- **Binary** — Unambiguous pass or fail
- **Independent** — Each tests one thing
- **Named clearly** — `assert_has_error_handling` not `assert_check_3`
- **Pure stdlib** — Only use `re`, `json`, `string`, etc. No external dependencies.

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
> - **Artifact**: [path] — [brief description of what it does]
> - **Runner**: [built-in SDK / custom command]
> - **Assertions**: [count] checks — [list names]
> - **Test cases**: [count] cases across [count] categories — [list categories]
>
> Ready to start the optimization loop?

Wait for confirmation before proceeding.

Then initialize `.autoresearch/`:

**Prompt mode** (no custom runner):

```bash
mkdir -p .autoresearch/prompts/candidates .autoresearch/prompts/history .autoresearch/results
cp <source-prompt> .autoresearch/prompts/current.txt
```

```json
{
  "artifact": "<path to source prompt>",
  "assertions": "<path to assertions file>",
  "test_cases": "<path to test cases file>",
  "model": "sonnet"
}
```

**Custom runner mode**:

```bash
mkdir -p .autoresearch/history .autoresearch/results
```

```json
{
  "artifact": "<path to artifact being optimized>",
  "runner": "<shell command to run assessment>",
  "assertions": "<path to assertions file>",
  "test_cases": "<path to test cases file>"
}
```

The `model` field is optional (defaults to `"sonnet"`, only used in prompt mode). The `runner` field triggers custom runner mode.

## Phase 2: Launch Optimization Loop

After setup is complete (or when resuming an existing config), launch the optimization loop in a subagent:

1. Read the loop instructions from `${CLAUDE_PLUGIN_ROOT}/agents/optimization-loop.md` (skip the YAML frontmatter)
2. Use the **Agent** tool with:
   - `prompt`: The loop instructions you just read, followed by any user constraints from $ARGUMENTS (e.g. "target 95% pass rate", "focus on auth category")
   - `run_in_background`: `false`
   - Do NOT set `subagent_type` — use the default general-purpose agent

Running in the foreground keeps the user in the loop — they can see progress, approve permissions, and the loop agent can spawn its own parallel subagents for candidate evaluation.

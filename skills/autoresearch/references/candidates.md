# AutoResearch Candidate Discovery

Heuristics for finding things in a repo worth optimizing with autoresearch.

A good autoresearch candidate has three traits:
1. **Clear pass/fail criteria** — you can write binary assertions
2. **Cheap to assess** — each variant can be scored in seconds to minutes
3. **Easy to vary** — you can produce meaningfully different candidates

## Prompt candidates

**File patterns to search:**
- `**/*.prompt`, `**/*.prompt.md`, `**/prompts/*.txt`, `**/prompts/*.md`
- `**/system_prompt*`, `**/instructions.md`, `**/persona*.md`
- Large string literals in code that build LLM system prompts

**Grep patterns for inline prompts:**
- `system_prompt\s*=` (Python/JS/TS LLM SDK usage)
- `systemPrompt:` (config objects)
- `"""` or `'''` multi-line strings > 20 lines near `anthropic`, `openai`, `query(`, `chat.completions`
- `ChatPromptTemplate`, `PromptTemplate` (LangChain)
- `.md` files in directories named `prompts/`, `templates/`, `instructions/`

**Signals of a strong candidate:**
- The prompt has explicit structure requirements ("output must contain...")
- There's visible dissatisfaction: TODO comments, commit messages like "tweak prompt", multiple iterations in git history
- There are existing test cases or examples of desired output
- The prompt is used in production but has no evals
- The prompt has grown large and is hard to reason about

**Weak signals (skip):**
- One-off prompts for exploratory work
- Prompts that produce subjective output (creative writing, opinions)
- Prompts with no clear "wrong" answer

## Performance candidates

**File patterns:**
- `pytest.ini`, `pyproject.toml` (tool.pytest), `jest.config.*`, `vitest.config.*`, `karma.conf.*`
- `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, `circleci/config.yml`
- `Makefile`, `justfile`, `package.json` (scripts)
- `Dockerfile`, `docker-compose.yml`
- `webpack.config.*`, `rollup.config.*`, `vite.config.*`, `next.config.*`
- `tsconfig.json`, `babel.config.*`
- Database migration files, query files

**Signals of a strong candidate:**
- CI config references long timeouts (`timeout-minutes: 20+`, `timeout: 30m+`)
- Test config has `--runInBand`, no parallelism, or explicit serial execution
- Large test fixtures or `beforeEach` hooks that look expensive
- Comments mentioning slowness ("TODO: speed up", "slow test", "flaky")
- Build outputs larger than reasonable (check `dist/`, `build/` sizes if tracked)
- Recent commits mentioning "timeout", "slow", "perf", "optimize"

**Things to measure:**
- Test suite wall time (`time pytest`, `time npm test`)
- Build time (`time npm run build`)
- Bundle size (`du -sh dist/`)
- Query execution time (EXPLAIN ANALYZE, slow query logs)

**Setup effort:** Medium — needs a custom runner script

## Quality/structure candidates

**File patterns:**
- Linter/formatter configs: `.eslintrc*`, `.prettierrc*`, `pyproject.toml` (ruff, black), `.rubocop.yml`
- Code review configs: `CODEOWNERS`, `.github/pull_request_template.md`, review checklists
- Doc templates: `README.md` templates, API doc generators, docstring conventions
- Accessibility configs: `a11y` rules, lighthouse configs
- Security scanning: `semgrep.yml`, `.trivyignore`, custom security rules

**Signals of a strong candidate:**
- The config already has explicit rules — these map directly to assertions
- There's a stated goal that isn't currently met (e.g., "all endpoints must have docs")
- Current output is inconsistent across files/modules
- Rules are subjective but could be made objective

**Setup effort:** Medium — needs a custom runner that runs the tool and captures output

## LLM integration points

**Where to look:**
- Any file importing `anthropic`, `openai`, `@anthropic-ai/sdk`, `langchain`, `llamaindex`, `@google/generative-ai`, `cohere`
- API route handlers that call LLM APIs
- Background jobs processing with LLMs
- Evaluation scripts that already exist

**Signals:**
- Multiple LLM calls chained together (could optimize the orchestration prompt)
- Prompts with placeholders/templates (can test across many inputs)
- Existing evaluation code that could inform test cases

## Repository-level signals

**Look for these to prioritize discovery:**
- `evals/`, `evaluations/`, `tests/prompts/`, `prompt_tests/` directories (existing eval infrastructure)
- `README` mentions of prompt engineering, LLM features, quality concerns
- Issue tracker labels: `prompt`, `performance`, `slow`, `quality`
- `CLAUDE.md` or `AGENTS.md` files referencing prompts or eval needs
- Existing `.autoresearch/` directory (resume previous work!)

## Anti-patterns (do not recommend)

Skip these even if they superficially look optimizable:

- **Subjective outputs** — "make the UI nicer", "improve tone" (no binary pass/fail)
- **Tasks requiring human judgment** — code review quality, design decisions
- **One-shot scripts** — optimization only pays off if you re-run
- **Things with no inputs to vary** — a deterministic transformation with no parameters
- **Hot paths with no measurable outcome** — "make the code cleaner" without metrics
- **Tasks where variants are expensive to test** — multi-hour integration tests per variant

## Presenting candidates to the user

When reporting findings, for each candidate include:

1. **Name** — short identifier
2. **Path** — file or directory
3. **Type** — prompt / performance / quality / LLM integration
4. **Signal** — what triggered detection (one line)
5. **Setup effort** — prompt mode (easy) or custom runner (medium)
6. **Quick start** — the command to begin: `/autoresearch <path>`

Rank by setup effort (easy first) and signal strength. Cap the list at 5-8 to avoid overwhelming the user.

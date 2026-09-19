# Demo Workflow

This walkthrough shows a complete first task for a new user. It uses a separate Git repository as the target workspace and keeps the orchestrator checkout unchanged.

## 1. Clone and Install

```bash
git clone --recurse-submodules https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator.git
cd gpt-deepseek-v1-orchestrator
python -m venv .venv
source .venv/bin/activate                 # macOS/Linux
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Install the DeepSeek Harness and verify it:

```bash
dsh --version
```

Create a separate target repository, or use an existing Git repository:

```bash
git clone https://github.com/example/sample-cli.git ../sample-cli
```

The target must be a Git workspace that the executor is allowed to modify.

## 2. Configure Providers

```bash
cp .env.example .env                 # PowerShell: Copy-Item .env.example .env
```

Export the values from `.env` using your shell or secrets manager. The values follow this shape:

```env
GPT_API_KEY=your-gpt-key
GPT_API_BASE=https://your-provider.example/v1
GPT_MODEL=your-planner-reviewer-model
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=your-deepseek-model
MAX_REVIEW_ITERATIONS=3
```

Do not commit `.env` or replace the placeholders with real keys in documentation.

## 3. Submit a Goal

For example, ask for a JSON output mode while preserving the existing text output:

```bash
orchestrator run "Add a --format json option to the CLI, preserve the existing text output by default, update the help text, and add tests for both formats" \
  --workspace ../sample-cli \
  --state-dir .orchestrator \
  --max-iterations 3 \
  --json
```

The workflow is:

```text
User input goal
      |
      v
GPT Planner
      |
      v
TaskContract
      |
      v
DeepSeek Executor
      |
      v
GPT Reviewer
      |
      +------ PASS ------> Completed task
      |
      +----- REVISE -----> DeepSeek repair -> GPT Reviewer
      |
      +---- BLOCKED ------> Save state -> human answer -> resume
```

## 4. What the Planner Produces

GPT Planner turns the goal into a structured contract containing:

- Goal interpretation
- Scope and non-goals
- Implementation plan
- Acceptance criteria
- Validation requirements
- Allowed paths and risk notes

The contract is saved with the task state before execution begins.

## 5. What the Executor Records

DeepSeek Harness reads the target repository, changes the required files, runs commands and tests, and returns evidence including:

- Harness session ID
- Changed files
- Git diff summary
- Command log
- Test results

## 6. Review and Automatic Repair

GPT Reviewer checks the original goal, TaskContract, diff, tests, and evidence.

- `PASS` completes the task.
- `REVISE` creates a repair task and sends it back to DeepSeek automatically.
- `BLOCKED` saves the state and waits for a human response.

A successful repair path looks like:

```text
DeepSeek first execution
        |
        v
GPT Reviewer: REVISE
        |
        v
DeepSeek automatic repair
        |
        v
GPT Reviewer: PASS
```

## 7. Inspect and Resume

Use the task ID printed by `run` to inspect progress:

```bash
orchestrator status TASK_ID --state-dir .orchestrator --json
```

If the process is interrupted, continue from the saved checkpoint:

```bash
orchestrator resume TASK_ID --state-dir .orchestrator --json
```

Resume keeps the original TaskContract, task ID, session context, and previous evidence. It does not start planning again or repeat completed phases.

When the task reaches `PASS`, inspect the target repository's diff and run its normal test command before committing the target project changes.

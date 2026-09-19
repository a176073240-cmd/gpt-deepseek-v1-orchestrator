# User Guide

GPT-DeepSeek V1 Orchestrator turns a natural-language coding goal into a controlled workflow: GPT creates a structured plan, DeepSeek Harness edits and tests the repository, and GPT reviews the evidence.

## Environment Requirements

- Python 3.10 or newer
- Git
- Node.js and pnpm for the DeepSeek Harness installation
- A GPT-compatible API provider
- A DeepSeek API account and the DeepSeek Harness command (`dsh`)
- Network access to the configured provider endpoints

The orchestrator works with one Git workspace at a time. Run it against a repository you can inspect and modify.

## Installation

Clone the repository with its pinned upstream components:

```bash
git clone --recurse-submodules https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator.git
cd gpt-deepseek-v1-orchestrator
python -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the local package:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Install DeepSeek Harness according to its upstream documentation. Verify it is available with:

```bash
dsh --version
```

If your Harness is a checked-out source tree, set `DSH_COMMAND` to its supported launcher before running the orchestrator.

## Configuration

Create a local environment file from the template:

```bash
# macOS/Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

The CLI reads exported environment variables. It does not automatically load `.env`, so load the file with your shell, a dotenv tool, or a secrets manager. For PowerShell, values can be set for the current session with `$env:NAME = "value"`.

Never commit `.env` or place credentials in task text, state files, logs, or screenshots.

## API Configuration

Set these values without including quotes around ordinary values:

```env
GPT_API_KEY=your-gpt-key
GPT_API_BASE=https://your-provider.example/v1
GPT_MODEL=your-planner-reviewer-model

DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=your-deepseek-model

MAX_REVIEW_ITERATIONS=3
```

`GPT_API_BASE` may point to OpenAI's API, an OpenAI-compatible service, or an enterprise proxy. Use the base URL and model name required by that provider. `DEEPSEEK_API_BASE` and `DEEPSEEK_MODEL` are passed to the Harness adapter. The smoke test can verify that both providers are reachable without changing a repository.

## Run a Task

Use an existing Git repository as the target workspace:

```bash
orchestrator run "Add a CSV export while preserving existing behavior" \
  --workspace /path/to/target-repository \
  --state-dir .orchestrator \
  --max-iterations 3 \
  --json
```

On Windows PowerShell, use one line or PowerShell's backtick for continuation:

```powershell
orchestrator run "Add a CSV export while preserving existing behavior" --workspace C:\work\target-repository --state-dir .orchestrator --max-iterations 3 --json
```

The command returns a task ID and advances through planning, execution, validation, and review. The JSON result includes the TaskContract, execution report, validation evidence, Git evidence, reviewer verdict, and DeepSeek session ID when available.

For an offline check that does not call providers:

```bash
python orchestrator.py run "Inspect this fixture" --workspace /path/to/git-fixture --fake --json
```

## View Task Status

Use the task ID returned by `run`:

```bash
orchestrator status TASK_ID --state-dir .orchestrator --json
```

The status includes the current phase, reviewer verdict, saved contract, checkpoints, evidence, and any human question waiting for an answer. State is stored locally under the selected state directory.

## Resume a Task

If a process stops during execution or validation, run:

```bash
orchestrator resume TASK_ID --state-dir .orchestrator --json
```

Resume reuses the saved TaskContract and prior evidence. It does not create a new plan or repeat completed phases. Use the same target checkout and state directory that were recorded for the task.

For a task waiting on a human decision:

```bash
orchestrator ask TASK_ID "Which compatibility policy should be used?" --context "Two existing formats are present." --state-dir .orchestrator --json
orchestrator answer TASK_ID "Keep the existing format and add the new one." --question-id QUESTION_ID --state-dir .orchestrator --json
orchestrator resume TASK_ID --state-dir .orchestrator --json
```

## Review Outcomes

- **PASS**: The reviewer found the goal and acceptance criteria satisfied. The task can be completed.
- **REVISE**: Evidence or implementation is incomplete. The orchestrator creates a repair task and sends it back to DeepSeek, then reviews the new result up to `MAX_REVIEW_ITERATIONS`.
- **BLOCKED**: Progress needs a human decision or missing configuration. The state and evidence are saved; provide the requested answer or configuration, then resume.

## Common Questions

### Does the orchestrator modify its own repository?

No. Pass the repository to change with `--workspace`. Keep the orchestrator checkout separate from the target project.

### Are API keys stored in Git?

No. Keep them in the process environment or ignored `.env`. Do not paste them into task prompts or commit them.

### Why does a task stop at BLOCKED?

A provider, Harness command, required configuration, or human policy decision may be missing. Run `status` to read the saved reason, resolve it, and use `resume`.

### Why did the reviewer return REVISE?

The implementation, tests, or evidence did not satisfy the TaskContract. The automatic repair loop will retry within the configured iteration limit. Inspect the saved evidence if it eventually stops.

### Can I run without live APIs?

Yes. Use `--fake` for deterministic offline smoke tests. Real planning and execution require valid provider credentials and a working DeepSeek Harness.

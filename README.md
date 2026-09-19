# GPT-DeepSeek V1 Orchestrator

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

[![Release](https://img.shields.io/badge/release-v1.1.0-2563eb)](https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator/releases/tag/v1.1.0)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-3776ab?logo=python&logoColor=white)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Executor](https://img.shields.io/badge/executor-DeepSeek%20Harness-5b21b6)](https://github.com/deepseek-ai/deepseek-harness)

> A durable coding workflow that combines GPT planning and review with DeepSeek Harness execution.

**Give it a goal and a Git repository. It creates a TaskContract, runs DeepSeek Harness, validates the changes, and asks an independent reviewer whether to pass, revise, or stop.**

GPT-DeepSeek V1 Orchestrator turns a natural-language engineering goal into a structured, reviewable workflow for an existing Git repository. A GPT-compatible model plans the task, DeepSeek Harness performs the work, deterministic checks collect evidence, and a GPT-compatible reviewer returns PASS, REVISE, or BLOCKED.

V1.1.0 includes persistence, resume, human escalation, and an evidence chain. It intentionally keeps the V1 planner → executor → reviewer architecture and does not introduce model routing, multi-agent scheduling, or a web UI.

## At a glance

| | |
| --- | --- |
| **Positioning** | A small, auditable orchestration layer for agent-assisted changes to existing Git repositories |
| **Workflow** | Plan → Execute → Validate → Review → Revise or resume |
| **Best for** | Teams that want durable contracts, reproducible evidence, and bounded automated repair |
| **Current status** | V1.1.0 released; V1.2-A open-source productization in progress |

**Start here:** [Download](#download) · [Quick Start](#quick-start) · [GUI Launcher](#windows-gui-launcher) · [Author's Recommended API Setup](#authors-recommended-api-setup) · [Guided Demo](docs/demo-workflow.md) · [Architecture](docs/architecture.md) · [User Guide](docs/user-guide.md)

## Why this project

A single prompt-to-code step is difficult to audit and recover. This project adds a small orchestration layer:

- planning is captured as a durable TaskContract;
- execution is separated from independent review;
- validation and Git evidence are retained with the task;
- reviewer feedback drives a bounded REVISE → PASS loop;
- interrupted work resumes without planning again;
- policy decisions can pause for explicit human input.

## Core capabilities

- **GPT Planner** — builds a structured contract with scope, non-goals, acceptance criteria, validation, allowed paths, and risks.
- **DeepSeek Harness Executor** — runs the contract in a target Git workspace through dsh and retains the observed session identity.
- **GPT Reviewer** — evaluates the implementation and evidence and returns PASS, REVISE, or BLOCKED.
- **Persistence and resume** — atomically checkpoints every phase and resumes the saved contract after interruption.
- **Evidence chain** — records validation, Git evidence, execution reports, reviewer feedback, and human answers.
- **Safety boundaries** — checks workspace paths, captures a Git baseline, and redacts configured secret values.
- **Offline mode** — provides a deterministic FakeAdapter for testing without live providers.

## Architecture

~~~mermaid
flowchart LR
    U[User goal] --> P[GPT Planner<br/>TaskContract]
    P --> E[DeepSeek Harness<br/>Executor]
    E --> V[Validation<br/>and Git evidence]
    V --> R[GPT Reviewer]
    R -->|REVISE| E
    R -->|PASS| C[Completed]
    R -->|BLOCKED| H[Human decision]
    H -->|answer + resume| E
    P -. checkpoint .-> S[(Atomic StateStore)]
    E -. checkpoint .-> S
    V -. checkpoint .-> S
    R -. checkpoint .-> S
~~~

The planner and reviewer use an OpenAI-compatible POST /chat/completions endpoint. The executor invokes DeepSeek Harness in the target repository. Runtime state is written under .orchestrator/ and ignored by Git. See [Architecture](docs/architecture.md).

## Features

- Structured and validated task contracts
- Headless DeepSeek Harness execution with bounded subprocess handling
- Validation commands plus Git status and diff evidence
- Automatic REVISE → PASS recovery with an iteration limit
- Durable ask, answer, status, and resume commands
- JSON output for automation
- Secret redaction and workspace boundary validation
- Deterministic tests with temporary Git fixtures

## Download

Windows users can download the latest desktop version:

**GPT-DeepSeek v1.2.0 Windows x64**

Download:

GitHub Releases: [https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator/releases/tag/v1.2.0](https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator/releases/tag/v1.2.0)

- Windows desktop application
- No Python installation required
- Includes GUI Launcher

## Installation

Requirements:

- Python 3.10 or newer
- Git
- DeepSeek Harness and Node.js for real execution
- An OpenAI-compatible API provider for real planning and review

~~~bash
git clone --recurse-submodules https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator.git
cd gpt-deepseek-v1-orchestrator
python -m venv .venv
~~~

Activate the environment and install the package:

~~~bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e .
~~~

Follow the [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) instructions for its prerequisites and source setup. See [Providers](docs/providers.md) and [Provider Setup](docs/provider-setup.md).

## Quick Start

### 30-second offline demo

Run the deterministic offline workflow first. It needs no provider credentials or live dsh process and lets you verify the full orchestration path before configuring a provider:

~~~bash
orchestrator run "Inspect this fixture" \
  --workspace /path/to/git-fixture \
  --fake \
  --json
~~~

Use any disposable Git repository for the workspace path. A successful run returns JSON with a completed phase, the generated task contract, validation evidence, and the reviewer verdict.

For a narrated real-provider flow, follow the [Guided Demo](docs/demo-workflow.md).

Without an installed package, use the repository shim:

~~~bash
python orchestrator.py run "Inspect this fixture" \
  --workspace /path/to/git-fixture \
  --fake \
  --json
~~~

## Windows GUI Launcher

GPT-DeepSeek v1.2.0 adds an optional PySide6 desktop entry point while keeping the existing
CLI and Agent architecture unchanged:

~~~powershell
python -m pip install -e ".[gui]"
Start-GPT-DeepSeek.bat
~~~

Double-click `Start-GPT-DeepSeek.bat` after setup, or run
`python launcher/main.py` directly. Enter a Task, select a project Workspace,
and select **开始执行**. The launcher
calls the existing `orchestrator run` workflow and displays live Planner,
Executor, Reviewer, and PASS/REVISE/BLOCKED state updates. See the
[GUI Launcher Guide](docs/gui-launcher.md).

End users can download the Windows ZIP and run `GPT-DeepSeek.exe` without
installing Python. See [Windows Installation](docs/installation-windows.md).

## Configuration

Copy .env.example to a local ignored file and provide values through your shell, secret manager, or dotenv tool. The CLI reads environment variables but does not load .env automatically.

| Variable | Required | Purpose |
| --- | --- | --- |
| GPT_API_KEY | Real runs | Credential for the OpenAI-compatible planner/reviewer endpoint |
| GPT_API_BASE | Real runs | Provider base URL or full /chat/completions URL |
| GPT_MODEL | Real runs | Planner and reviewer model name |
| DEEPSEEK_API_KEY | Real execution | Credential exposed to DeepSeek Harness |
| DEEPSEEK_API_BASE | Real execution | DeepSeek-compatible provider base URL |
| DEEPSEEK_MODEL | Provider-dependent | Model made available to DeepSeek Harness |
| DSH_COMMAND | Source setups | Supported command used to launch DeepSeek Harness |
| MAX_REVIEW_ITERATIONS | No | Maximum review/repair iterations; default 3 |

Never commit credentials, local environment files, state, sessions, logs, or runtime output.

## Author's Recommended API Setup

During the development and real-provider validation of GPT-DeepSeek Orchestrator, the author personally used the following OpenAI-compatible API provider:

### Modelflare

Registration:

[https://modelflare.dev/sign-up?partner=IEQJUO5IKYU8](https://modelflare.dev/sign-up?partner=IEQJUO5IKYU8)

API Base:

[https://modelflare.dev/v1](https://modelflare.dev/v1)

- Used by the author during V1.1 development and validation
- Compatible with OpenAI-style API interfaces
- Suitable for configuring GPT Planner, GPT Reviewer, and DeepSeek providers

This is a personal recommendation based on the author's usage experience.

Modelflare is an independent third-party service.

This project is not affiliated with or officially endorsed by Modelflare.

Users are free to choose any compatible OpenAI-compatible API provider.

The registration URL contains a partner identifier. Review the provider's current terms, privacy policy, pricing, model availability, and data-retention practices before use. See [Providers](docs/providers.md) for provider-neutral guidance.
## Usage

Run a real task:

~~~bash
orchestrator run "Add CSV export while preserving existing behavior" \
  --workspace /path/to/target-repository \
  --state-dir .orchestrator \
  --max-iterations 3 \
  --json
~~~

Inspect or resume a saved task:

~~~bash
orchestrator status TASK_ID --state-dir .orchestrator --json
orchestrator resume TASK_ID --state-dir .orchestrator --json
~~~

Pause for a human decision, record the answer, and resume:

~~~bash
orchestrator ask TASK_ID "Which compatibility policy should be used?" \
  --context "Two existing formats are present." \
  --state-dir .orchestrator --json

orchestrator answer TASK_ID "Keep the existing format." \
  --question-id QUESTION_ID \
  --state-dir .orchestrator --json

orchestrator resume TASK_ID --state-dir .orchestrator --json
~~~

See the [User Guide](docs/user-guide.md) and [Demo Workflow](docs/demo-workflow.md).

## Development and validation

~~~bash
python -m pytest
python -m compileall -q src launcher orchestrator.py
~~~

Tests use temporary Git fixtures and do not require live providers. Archived V1.1 validation assets are under [validation/](validation/).

## Roadmap

- **V1.1.0 — released:** planner, executor, reviewer loop, resume, evidence chain, guides, demo, and validation archive.
- **V1.2 GUI Launcher MVP:** optional PySide6 Windows entry point wrapping the existing CLI.
- **V1.2-A — in progress:** localization, provider documentation, attribution, licensing clarity, and GitHub presentation.
- **Future candidates:** packaging polish, more provider examples, CI/release automation, and optional observability. These are not current features.

## License

Original project code and documentation are licensed under the [Apache License 2.0](LICENSE).

## Patent Notice

Apache-2.0 Section 3 grants a patent license from each Contributor for patent claims that the Contributor can license and that are necessarily infringed by its Contribution alone or with the Work. The grant is subject to the license terms, including its patent-litigation termination provision. This summary adds no separate patent grant or warranty; the [LICENSE](LICENSE) text controls.

## Third-party Attribution

This repository pins third-party source components, including DeepSeek Harness and Augani Agent Orchestrator. They remain under their respective MIT licenses and are not relicensed under this project's Apache-2.0 license. See [Third-party Attribution](docs/third-party.md).

## Documentation

- [Windows Installation](docs/installation-windows.md)
- [GUI Launcher Guide](docs/gui-launcher.md)
- [User Guide](docs/user-guide.md)
- [Demo Workflow](docs/demo-workflow.md)
- [Architecture](docs/architecture.md)
- [Providers](docs/providers.md)
- [Provider Setup](docs/provider-setup.md)
- [Third-party Attribution](docs/third-party.md)
- [Contributing](CONTRIBUTING.md)

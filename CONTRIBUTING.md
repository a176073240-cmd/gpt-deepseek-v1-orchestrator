# Contributing

Thank you for helping improve GPT-DeepSeek V1 Orchestrator. Keep contributions focused on the V1 workflow and its reliability. New V2 capabilities, unrelated dependencies, and broad architecture rewrites are outside the current release scope.

## Set up a checkout

Use Python 3.10 or newer, Git, and a virtual environment. Clone submodules when you need to inspect or work with the pinned upstream components:

```bash
git clone --recurse-submodules https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator.git
cd gpt-deepseek-v1-orchestrator
python -m venv .venv
```

Activate the environment for your shell and install the package:

```bash
python -m pip install -e .
```

Do not commit `.env`, API keys, provider responses, runtime state, logs, or credentials. Use `.env.example` as the template for local configuration.

## Make and verify a change

Keep changes small and explain the user-visible behavior in the commit or pull request. Add or update a focused test when a change affects a contract, workflow transition, persistence behavior, adapter, or security boundary.

Run the checks before opening a pull request:

```bash
python -m pytest
python -m compileall -q src orchestrator.py
git diff --check
```

The default tests are offline and use temporary Git fixtures. Live provider checks should only be run with credentials kept outside the repository; remove any generated state and logs before sharing a patch.

## Pull requests

Describe the problem, the resulting behavior, and the validation you ran. Include any compatibility or migration concern that a reviewer should know. Keep the public documentation and `.env.example` synchronized with CLI or configuration changes.

Use a descriptive branch and commit message. Do not include secrets or private paths in commits, issue reports, screenshots, or logs. A maintainer will review scope, tests, security boundaries, and documentation before merging.

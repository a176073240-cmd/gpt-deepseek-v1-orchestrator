# Contributing

Thank you for helping improve GPT-DeepSeek V1 Orchestrator. Contributions should preserve the focused Planner → DeepSeek Harness Executor → Reviewer workflow and its auditability.

## Before you start

- Search existing issues before opening a new one.
- Use the bug report or feature request template so maintainers receive reproducible context.
- For a large behavior change, open an issue before implementation to confirm scope.
- Do not post credentials, private repository content, personal paths, provider responses, state files, or logs containing sensitive data.

Bug fixes, documentation, tests, portability improvements, and small reliability changes are welcome. Broad architecture rewrites, unrelated dependencies, and unplanned V2 capabilities should be discussed first.

## Development setup

Requirements are Python 3.10 or newer and Git. Node.js and DeepSeek Harness are needed only for live executor work.

~~~bash
git clone --recurse-submodules https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator.git
cd gpt-deepseek-v1-orchestrator
python -m venv .venv
~~~

Activate the environment for your shell and install the package:

~~~bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e .
~~~

If you cloned without submodules:

~~~bash
git submodule update --init --recursive
~~~

Use .env.example only as a configuration reference. Keep real credentials in your shell or secret manager and never commit a local .env file.

## Making a change

1. Create a focused branch.
2. Keep the change small and avoid unrelated formatting.
3. Add or update tests when behavior changes.
4. Update public documentation when commands, configuration, or user-visible behavior changes.
5. Preserve compatibility unless the issue and pull request clearly document a required migration.

Changes to TaskContract, workflow transitions, persistence, adapters, security boundaries, or the Agent architecture require focused tests and explicit rationale.

## Validation

Run the offline checks from the repository root:

~~~bash
python -m pytest
python -m compileall -q src orchestrator.py
git diff --check
~~~

The default tests use temporary Git fixtures and do not require provider credentials or a live dsh process. Run live provider checks only when needed, keep credentials outside the repository, and remove generated runtime data before sharing a patch.

## Commit and pull request guidance

Use a concise, imperative commit subject. A pull request should explain:

- the problem and why it matters;
- the chosen approach;
- user-visible behavior and compatibility impact;
- tests and manual checks performed;
- documentation or migration steps, when applicable.

Before requesting review, confirm:

- [ ] The change is limited to the stated scope.
- [ ] Tests and git diff --check pass.
- [ ] No credentials, tokens, local paths, logs, sessions, state, caches, or runtime outputs are included.
- [ ] Documentation and examples match the implementation.
- [ ] Third-party code or assets include the required license and attribution information.

## Reporting security-sensitive problems

Do not publish exploitable details or credentials in a public issue. Use a private maintainer contact channel when one is available. If no private channel is listed, open a minimal issue requesting a secure contact method without including sensitive details.

## License

By submitting a contribution, you agree that your contribution may be distributed under the repository's [Apache License 2.0](LICENSE). Third-party components retain their own licenses as documented in [Third-party Attribution](docs/third-party.md).

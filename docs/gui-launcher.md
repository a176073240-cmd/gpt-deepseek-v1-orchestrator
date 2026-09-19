# V1.2 GUI Launcher

The V1.2 launcher is a small Windows desktop shell around the existing
orchestrator CLI. It does not contain Planner, Executor, Reviewer, TaskContract,
or workflow state-machine logic.

## Install

From the repository root, create or activate a Python 3.10+ environment and
install the GUI extra:

~~~powershell
python -m pip install -e ".[gui]"
~~~

Real runs still need the same GPT and DeepSeek Harness environment variables as
the CLI. See [Provider Setup](provider-setup.md).

## Start

~~~powershell
python launcher/main.py
~~~

In **GPT-DeepSeek Assistant**:

1. Enter a natural-language Task.
2. Select an existing Git project as the Workspace.
3. Select **开始执行**.
4. Follow Planner, Executor, validation, Reviewer, and verdict events in Logs.

The status badge is `Running` while the subprocess is active, `Completed` for a
successful `PASS`, and `Failed` for CLI errors or `BLOCKED`. A `REVISE` verdict
appears in the log before the next Executor iteration.

## How it works

`launcher/runner.py` starts the repository's existing `orchestrator.py run`
shim asynchronously. It passes the selected workspace with `--workspace` and
uses the existing `.orchestrator/` state store. The launcher polls those atomic
state files to report phase changes while the CLI is running. No Agent behavior
is duplicated in the GUI.

Closing the window during a run offers to terminate the CLI process. Its last
persisted state remains available to the existing CLI `resume` command.

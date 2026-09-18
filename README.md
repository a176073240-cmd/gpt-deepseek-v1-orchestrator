# GPT / DeepSeek V1 Orchestrator

这是一个面向 Git 仓库的、可恢复的 V1 编排器。用户输入模糊目标后，系统按以下链路工作：

`User Goal → GPT-compatible Planner → DeepSeek Harness Executor → Validation → GPT-compatible Reviewer → PASS / REVISE / BLOCKED`

本次备份时 V1 开发已暂停。仓库保存当前实现快照，后续验收计划仍保留在本文档中。

## 当前架构

- `GPTCompatibleAdapter`：通过 OpenAI-compatible `/chat/completions` API 负责规划和评审。
- `DeepSeekHarnessAdapter`：以 headless `dsh` 子进程执行任务，并保存 DeepSeek session identity。
- `Orchestrator`：驱动 `PLANNING → EXECUTING → VALIDATING → REVIEWING`，处理 `PASS`、`REVISE`、`BLOCKED` 和最大迭代次数。
- `StateStore`：以原子替换写入每个任务的 JSON 状态，支持退出后 `resume`。
- `security.py`：限制 Git workspace、收集 Git baseline/diff，并对凭证和运行输出做脱敏。
- `FakeAdapter`：离线演示和集成测试使用的确定性适配器。

上游组件以 Git submodule 指针保存：

- [Augani/agent-orchestrator](https://github.com/Augani/agent-orchestrator)
- [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)

## 已完成模块

- 结构化 `TaskContract`、`ExecutionReport`、`ReviewResult` 和持久化 `OrchestrationState`。
- GPT-compatible Planner/Reviewer 适配器和 JSON contract/verdict 解析。
- DeepSeek Harness headless 调用、session id 记录及恢复参数传递。
- Git 仓库检查、baseline/diff 采集、workspace 路径边界和凭证脱敏。
- CLI 的 `run`、`resume`、`status`、`ask`、`answer` 命令。
- FakeAdapter 离线场景与基础单元/集成测试文件。

Validation 当前会收集 Git 状态证据；按 contract 执行任意项目验证命令、对 executor 变更文件做完整白名单校验等项目仍列入后续 V1 验收工作。

## 安装和运行

```powershell
python -m pip install -e . --no-deps

# 离线演示
python -m v1_orchestrator.cli run "整理这个项目" --workspace C:\path\to\git-repo --fake --json

# 真实 provider（先配置下方环境变量，并确保 dsh 可执行）
orchestrator run "让这个项目增加断点续传功能" --workspace C:\path\to\git-repo

# 从持久化状态恢复
orchestrator resume <task-id> --state-dir .orchestrator
orchestrator status <task-id> --state-dir .orchestrator --json
```

默认状态目录是当前目录下的 `.orchestrator/`；它已加入 `.gitignore`，不会进入提交。运行日志和 provider 输出只作为内存/状态证据处理，凭证来自环境变量且会脱敏。

需要的环境变量：

```text
GPT_API_BASE
GPT_API_KEY
GPT_MODEL
DEEPSEEK_API_BASE
DEEPSEEK_API_KEY
DEEPSEEK_MODEL
MAX_REVIEW_ITERATIONS   # 可选，默认 3
```

## 后续 V1 验收计划

1. **A — Planning**：使用真实 GPT-compatible provider 生成完整 Task Contract 和 Acceptance Criteria。
2. **B — Execution**：让 DeepSeek Harness 修改隔离的测试仓库并运行验证命令。
3. **C — Review Retry**：制造不完整实现，确认 `REVISE → EXECUTING → REVIEWING` 自动循环并受最大迭代次数限制。
4. **D — Resume**：在执行阶段终止进程，重新 `resume`，确认不重复规划已完成步骤并保留 session identity。
5. **E — Blocked**：制造需要人工决策的场景，确认 BLOCKED 状态、`ask`/`answer` 和恢复路径。

真实 API 验收需要用户提供对应 provider 的有效凭证和可运行的 DeepSeek Harness；在这些条件满足前，本仓库保持当前可审阅的实现快照。

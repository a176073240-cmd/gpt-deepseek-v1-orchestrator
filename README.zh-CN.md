# GPT-DeepSeek V1 Orchestrator

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

> 将 GPT 的规划与审查能力和 DeepSeek Harness 执行能力结合起来的持久化编码工作流。

**只需提供一个目标和 Git 仓库：系统会生成 TaskContract、运行 DeepSeek Harness、验证变更，并由独立 Reviewer 决定通过、修订或停止。**

GPT-DeepSeek V1 Orchestrator 将自然语言工程目标转换成面向现有 Git 仓库、结构化且可审查的工作流。兼容 GPT 的模型负责规划，DeepSeek Harness 执行变更，确定性检查收集证据，兼容 GPT 的 Reviewer 返回 PASS、REVISE 或 BLOCKED。

V1.1.0 已包含持久化、恢复、人工决策与证据链，并保持 V1 的 Planner → Executor → Reviewer 架构，不包含模型路由、多 Agent 调度或 Web UI。

## 为什么需要这个项目

一次性的 prompt-to-code 流程难以审计和恢复。本项目增加了轻量编排层：

- 使用持久化 TaskContract 保存规划；
- 将执行与独立审查分离；
- 随任务保留验证结果与 Git 证据；
- 通过有次数上限的 REVISE → PASS 循环修订；
- 中断后无需重新规划即可恢复；
- 策略选择可暂停并等待明确的人工输入。

## 核心能力

- **GPT Planner** — 生成包含范围、非目标、验收标准、验证、允许路径和风险的结构化合同。
- **DeepSeek Harness Executor** — 通过 dsh 在目标 Git 工作区执行合同并保留会话标识。
- **GPT Reviewer** — 审查实现与证据，返回 PASS、REVISE 或 BLOCKED。
- **持久化与恢复** — 原子化保存每个阶段，并从已保存合同继续。
- **证据链** — 记录验证、Git 证据、执行报告、审查反馈与人工答复。
- **安全边界** — 检查工作区路径、捕获 Git 基线并脱敏已配置的秘密值。
- **离线模式** — 使用确定性的 FakeAdapter，在无实时 Provider 时测试。

## Architecture

~~~mermaid
flowchart LR
    U[用户目标] --> P[GPT Planner<br/>TaskContract]
    P --> E[DeepSeek Harness<br/>Executor]
    E --> V[验证与 Git 证据]
    V --> R[GPT Reviewer]
    R -->|REVISE| E
    R -->|PASS| C[完成]
    R -->|BLOCKED| H[人工决策]
    H -->|答复并恢复| E
    P -. 检查点 .-> S[(原子 StateStore)]
    E -. 检查点 .-> S
    V -. 检查点 .-> S
    R -. 检查点 .-> S
~~~

Planner 与 Reviewer 使用兼容 OpenAI 的 POST /chat/completions 接口。Executor 在目标仓库调用 DeepSeek Harness。运行状态写入 .orchestrator/ 并由 Git 忽略。详见 [Architecture](docs/architecture.md)。

## Features

- 结构化且经过验证的 TaskContract
- 有界子进程的无头 DeepSeek Harness 执行
- 验证命令以及 Git status/diff 证据
- 带迭代上限的自动 REVISE → PASS
- 持久化 ask、answer、status 与 resume 命令
- 面向自动化的 JSON 输出
- 秘密值脱敏与工作区边界检查
- 使用临时 Git fixture 的确定性测试

## Installation

要求：Python 3.10+、Git；真实执行还需要 Node.js、DeepSeek Harness 与兼容 OpenAI 的 API Provider。

~~~bash
git clone --recurse-submodules https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator.git
cd gpt-deepseek-v1-orchestrator
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
~~~

按照 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 文档准备源码环境。Provider 配置见 [Providers](docs/providers.md) 与 [Provider Setup](docs/provider-setup.md)。

## Quick Start

先运行无需 Provider 凭据和实时 dsh 的离线测试：

~~~bash
orchestrator run "Inspect this fixture" --workspace /path/to/git-fixture --fake --json
~~~

未安装包时可运行：

~~~bash
python orchestrator.py run "Inspect this fixture" --workspace /path/to/git-fixture --fake --json
~~~

## Windows GUI Launcher

V1.2 新增可选的 PySide6 Windows 图形入口，现有 CLI 与 Agent 架构保持不变：

~~~powershell
python -m pip install -e ".[gui]"
python launcher/main.py
~~~

输入 Task、选择项目 Workspace 后点击 **开始执行**。启动器调用现有
`orchestrator run` 工作流，并实时显示 Planner、Executor、Reviewer 以及
PASS/REVISE/BLOCKED 状态。详见 [GUI Launcher 指南](docs/gui-launcher.md)。

## Configuration

将 .env.example 复制为本地忽略文件，通过 shell、秘密管理器或 dotenv 工具提供变量。CLI 不会自动加载 .env。

| 变量 | 何时需要 | 用途 |
| --- | --- | --- |
| GPT_API_KEY / GPT_API_BASE / GPT_MODEL | 真实运行 | Planner 与 Reviewer 的兼容 OpenAI Provider |
| DEEPSEEK_API_KEY / DEEPSEEK_API_BASE | 真实执行 | DeepSeek Harness Provider |
| DEEPSEEK_MODEL | 取决于 Provider | 提供给 Harness 的模型 |
| DSH_COMMAND | 源码环境 | 启动 DeepSeek Harness 的命令 |
| MAX_REVIEW_ITERATIONS | 可选 | 最大审查/修订次数，默认 3 |

不要提交凭据、本地环境文件、state、sessions、logs 或运行输出。

## 作者推荐 API 配置

在 GPT-DeepSeek Orchestrator 的开发和真实 Provider 验证过程中，作者本人实际使用以下 OpenAI-compatible API 服务。

### Modelflare

注册链接：

[https://modelflare.dev/sign-up?partner=IEQJUO5IKYU8](https://modelflare.dev/sign-up?partner=IEQJUO5IKYU8)

API Base：

[https://modelflare.dev/v1](https://modelflare.dev/v1)

- 作者本人在 V1.1 开发阶段实际使用
- 用于真实 Provider 验证
- 可用于 GPT Planner、GPT Reviewer 和 DeepSeek Provider 配置

该推荐基于作者个人使用体验。

Modelflare 是独立第三方服务。

本项目与 Modelflare 没有官方合作关系。

用户可以自由选择其他兼容 OpenAI API 的服务。

注册链接包含 partner 标识。使用前请自行确认服务条款、隐私政策、价格、模型可用性和数据保留政策。通用配置见 [Providers](docs/providers.md)。
## Usage

~~~bash
orchestrator run "Add CSV export while preserving existing behavior" \
  --workspace /path/to/target-repository --state-dir .orchestrator \
  --max-iterations 3 --json

orchestrator status TASK_ID --state-dir .orchestrator --json
orchestrator resume TASK_ID --state-dir .orchestrator --json
orchestrator ask TASK_ID "Which compatibility policy should be used?" --state-dir .orchestrator --json
orchestrator answer TASK_ID "Keep the existing format." \
  --question-id QUESTION_ID --state-dir .orchestrator --json
~~~

完整流程见 [User Guide](docs/user-guide.md) 与 [Demo Workflow](docs/demo-workflow.md)。

## Development and validation

~~~bash
python -m pytest
python -m compileall -q src launcher orchestrator.py
~~~

测试使用临时 Git fixture，不需要实时 Provider。V1.1 验证资产位于 [validation/](validation/)。

## Roadmap

- **V1.1.0 — 已发布：** Planner、Executor、Reviewer 循环、恢复、证据链、指南、演示与验证归档。
- **V1.2 GUI Launcher MVP：** 可选的 PySide6 Windows 图形入口，封装现有 CLI。
- **V1.2-A — 进行中：** 多语言 README、Provider 文档、第三方声明、许可证说明和 GitHub 展示。
- **未来候选：** 打包优化、更多 Provider 示例、CI/发布自动化和可选可观测性；这些不是当前功能。

## License

原创代码与文档采用 [Apache License 2.0](LICENSE)。

## Patent Notice

Apache-2.0 第 3 节由各 Contributor 就其有权许可、且其 Contribution 单独或与本 Work 结合时必然侵权的专利权利要求提供专利许可。该授权受许可证条款及专利诉讼终止条款约束。本说明不增加额外专利授权或保证，以 [LICENSE](LICENSE) 原文为准。

## Third-party Attribution

仓库固定了 DeepSeek Harness 与 Augani Agent Orchestrator 等第三方源码。它们继续适用各自的 MIT 许可证，不因本项目的 Apache-2.0 而重新许可。详见 [Third-party Attribution](docs/third-party.md)。

## Documentation

[GUI Launcher 指南](docs/gui-launcher.md) · [User Guide](docs/user-guide.md) · [Demo Workflow](docs/demo-workflow.md) · [Architecture](docs/architecture.md) · [Providers](docs/providers.md) · [Provider Setup](docs/provider-setup.md) · [Third-party Attribution](docs/third-party.md) · [Contributing](CONTRIBUTING.md)

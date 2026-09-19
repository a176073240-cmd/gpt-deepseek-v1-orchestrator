# V1.2 GUI Launcher

The V1.2 launcher is a Windows desktop shell around the existing orchestrator
CLI. It does not contain or replace Planner, Executor, Reviewer, TaskContract,
or workflow state-machine logic.

## 小白快速开始

### 1. 准备 Python

安装 Python 3.10 或更高版本。使用 Python 官方安装程序时，请勾选
**Add Python to PATH**。

首次安装项目依赖时，在项目目录打开 PowerShell，运行：

~~~powershell
py -3 -m pip install -e ".[gui]"
~~~

如果跳过这一步，`Start-GPT-DeepSeek.bat` 会检测 PySide6，并询问是否自动
安装 GUI 依赖。

### 2. 配置 GPT API

Launcher 与 CLI 使用同一组环境变量：

- `GPT_API_KEY`
- `GPT_API_BASE`
- `GPT_MODEL`

例如，以下命令会把配置保存到当前 Windows 用户。请把示例值替换为你的
Provider 信息，不要把真实密钥提交到 Git：

~~~powershell
[Environment]::SetEnvironmentVariable("GPT_API_KEY", "replace-with-your-key", "User")
[Environment]::SetEnvironmentVariable("GPT_API_BASE", "https://provider.example/v1", "User")
[Environment]::SetEnvironmentVariable("GPT_MODEL", "your-model", "User")
~~~

设置后关闭并重新打开 Launcher。项目不会自动读取 `.env` 文件。

### 3. 配置 DeepSeek Harness

真实执行需要以下环境变量：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_API_BASE`（也接受 Harness 使用的 `DEEPSEEK_BASE_URL`）
- `DEEPSEEK_MODEL`

还需要让 `dsh` 命令位于 Windows `PATH`。可先在新的 PowerShell 中验证：

~~~powershell
dsh --version
~~~

完整 Provider 与 Harness 安装说明见 [Provider Setup](provider-setup.md)。

### 4. 一键启动

双击项目根目录的：

~~~text
Start-GPT-DeepSeek.bat
~~~

脚本会优先使用 `.venv`，否则查找 `py -3` 或 `python`，并检查 Python
版本和 PySide6。也可以手动启动：

~~~powershell
python launcher/main.py
~~~

### 5. 完成界面检查

窗口顶部显示当前配置状态：

- **Python 环境**：Python 与 PySide6 是否满足要求；
- **GPT API**：必需环境变量是否齐全；
- **DeepSeek Harness**：DeepSeek 环境变量和 `dsh` 命令是否可用；
- **Workspace**：所选目录是否是 Git 仓库，并且 Git 可以读取。

绿色表示检查通过，红色会列出缺少的项目和处理方法。修改系统环境变量后，
请重启 Launcher；也可以点击 **重新检查配置** 刷新当前进程可见的配置。

API 状态中的“配置已就绪”表示必需变量已经提供。为避免未经同意地产生模型
费用，Launcher 不会在启动时发送测试请求；真实网络连接和密钥有效性会在执行
第一个任务时验证。

### 6. 运行任务

1. 在 **Task** 中输入自然语言目标；
2. 点击 **选择项目目录**，选择需要修改的 Git 仓库；
3. 确认配置和 Workspace 均显示为可用；
4. 点击 **开始执行**；
5. 在 Logs 中查看 Planner、Executor、Reviewer 和 PASS/REVISE/BLOCKED。

状态徽标含义：

- `Running`：CLI 正在执行；
- `Completed`：Reviewer 返回 `PASS`；
- `Failed`：CLI 出错或工作流进入 `BLOCKED`。

## 常见问题

### 未找到 Python

安装 Python 3.10+ 并启用 **Add Python to PATH**，然后重新双击启动脚本。

### GPT API 显示“需要设置”

补齐 `GPT_API_KEY`、`GPT_API_BASE` 和 `GPT_MODEL`，关闭后重新启动 GUI。

### DeepSeek Harness 显示“需要设置”

补齐 DeepSeek 环境变量，并确认新的 PowerShell 可以执行 `dsh --version`。

### Workspace 无效

Workspace 必须是包含 `.git` 的现有 Git 仓库，而不是普通文件夹或仓库外层目录。

### 执行失败

GUI 会显示简短错误提示；详细原因保留在 Logs。Provider 拒绝、网络错误、
Harness 启动失败和 `BLOCKED` 原因都可以在日志中查看。

## Architecture

`launcher/runner.py` asynchronously starts the repository's existing
`orchestrator.py run` shim, passes the selected workspace through `--workspace`,
and uses the existing `.orchestrator/` state store. The GUI polls those atomic
state files to display phase changes. No Agent behavior is duplicated.

Closing the window during a run offers to terminate the CLI process. Its last
persisted state remains available to the existing CLI `resume` command.

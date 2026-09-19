# V1.2.1 Zero Setup GUI Launcher

GPT-DeepSeek v1.2.1 的 Windows GUI 负责启动和显示现有 orchestrator；Planner、Executor、Reviewer、TaskContract 与 workflow 未被复制或修改。

## First launch guide

1. 双击 `GPT-DeepSeek.exe`（源码运行可执行 `python launcher/main.py`）。
2. 首次启动向导依次显示 **Environment Check → API Configuration → Connection Test → Ready**。
3. 在 API Configuration 填写提供商信息，点击 Finish；向导会把设置保存到本机安装目录的 `.env`。
4. 点击 **Run Demo** 可创建一个隔离的 demo fixture、运行内置测试并看到 `PASS`，不需要 API 或 Harness。
5. 真实任务中选择 Git workspace，填写任务目标，然后点击“开始执行”。

## Harness 自动发现

启动器按以下顺序寻找 Harness：

1. EXE 同目录、`harness/` 或 `bin/` 下的 bundled `dsh.exe`/`dsh.cmd`；
2. Settings 或环境变量 `DEEPSEEK_HARNESS_PATH`、`DSH_PATH`、`GPTDS_HARNESS_PATH` 指定的路径；
3. Windows `PATH` 中的 `dsh`；
4. 显示 `✗ Missing` 和解决方法。

准备好后 GUI 会显示 `Harness: ✓ Available`。自定义路径应指向可以接受标准 dsh 参数的 launcher。

## API setup

Settings 支持以下字段：

- `GPT_API_KEY`, `GPT_API_BASE`, `GPT_MODEL`
- `DEEPSEEK_API_KEY`, `DEEPSEEK_API_BASE`, `DEEPSEEK_MODEL`
- 可选 Harness 路径：`DEEPSEEK_HARNESS_PATH`

`.env` 只保存在本机，已被 `.gitignore` 排除。不要把密钥写进源代码、任务状态、日志或提交记录；本项目不会在界面日志中显示密钥。`DEEPSEEK_API_BASE` 会同时作为 Harness 的 `DEEPSEEK_BASE_URL` 兼容值。

## Connection Test

向导的 Connection Test 检查字段是否完整并验证 Harness 是否可发现，不会自动发送模型请求，也不会产生 API 费用。真实网络连接在第一次任务执行时由现有 CLI 验证。

## Troubleshooting

### Harness 显示 Missing

安装 DeepSeek Harness，或在 Settings 填写 `dsh.exe`/`dsh.cmd` 的完整路径。也可以在新的 PowerShell 中运行 `dsh --version`，确认它已加入 PATH，然后点击“重新检查配置”。

### API 显示需要设置

确认六个 API 字段没有空值，保存后点击“重新检查配置”。关闭并重新打开 EXE 也会重新读取 `.env`。

### EXE 无法启动

请使用 Windows x64 包中的 `GPT-DeepSeek.exe`，不要直接运行临时构建目录里的 DLL。源码运行需要 Python 3.10+ 与 `PySide6`；`Start-GPT-DeepSeek.bat` 会检测并提示安装 GUI 依赖。

### Workspace 无效

Workspace 必须是包含 `.git` 的现有 Git 仓库。普通文件夹、仓库父目录或无法执行 `git rev-parse` 的目录都会被拒绝。

### 任务执行失败

查看 Logs 中的 `[CLI error]`、`[Workflow] BLOCKED` 和 `[Reviewer]` 行。GUI 只负责进程生命周期与状态显示，任务状态仍由现有 `.orchestrator/` store 保存。

## Packaging

运行 `packaging/build-windows.ps1` 会生成 `dist/GPT-DeepSeek/GPT-DeepSeek.exe` 及 `GPT-DeepSeek-v1.2.1-windows-x64.zip`。如果发布包需要携带真实 bundled Harness，请把其 launcher 放入 `packaging/bundled-harness/` 后再构建；没有该目录时构建仍然成功，并使用配置路径或 PATH resolver。


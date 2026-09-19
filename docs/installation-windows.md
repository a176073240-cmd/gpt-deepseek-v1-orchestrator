# Windows Installation — GPT-DeepSeek v1.2.0

The Windows desktop package includes Python, PySide6, and the GPT-DeepSeek
orchestrator. End users do not need to install Python.

## 普通用户安装流程

### 1. 下载

从项目的 GitHub Releases 页面下载 GPT-DeepSeek v1.2.0 Windows ZIP 包。

### 2. 解压

把 ZIP 完整解压到一个可写目录，例如：

~~~text
C:\Users\你的用户名\Apps\GPT-DeepSeek
~~~

不要只复制 `GPT-DeepSeek.exe`。`_internal` 目录和
`GPT-DeepSeek-CLI.exe` 都是运行所需文件，必须保留原有相对位置。

### 3. 配置 API

在 Windows 开始菜单搜索 **编辑账户的环境变量**，新增以下用户变量：

| 变量 | 内容 |
| --- | --- |
| `GPT_API_KEY` | GPT-compatible Provider 提供的密钥 |
| `GPT_API_BASE` | Provider API 地址，例如 `https://provider.example/v1` |
| `GPT_MODEL` | Planner 与 Reviewer 使用的模型名 |
| `DEEPSEEK_API_KEY` | DeepSeek Provider 密钥 |
| `DEEPSEEK_API_BASE` | DeepSeek Provider API 地址 |
| `DEEPSEEK_MODEL` | Harness 使用的模型名 |

不要把 API Key 写入下载目录、`.env`、截图或反馈日志。设置完成后关闭已经
打开的 GPT-DeepSeek 窗口，再重新启动。

DeepSeek Harness 是外部执行器。需要按项目的
[Provider Setup](provider-setup.md) 安装，并确保新的 PowerShell 可以运行：

~~~powershell
dsh --version
~~~

### 4. 双击 EXE

双击：

~~~text
GPT-DeepSeek.exe
~~~

首次打开时，窗口顶部会检查 Python 运行时、GPT API 配置、DeepSeek
Harness 和 Workspace。绿色表示可用，红色会说明缺少什么。

Windows SmartScreen 可能会提示未识别的应用，因为当前构建未进行商业代码
签名。请只使用项目官方 Release 下载的文件，并在继续前核对发布说明。

## 使用

1. 输入 Task；
2. 选择一个现有 Git 仓库作为 Workspace；
3. 确认所有检查显示可用；
4. 点击 **开始执行**；
5. 在日志窗口查看 Planner、Executor、Reviewer 和最终 verdict。

GUI 的持久化任务状态保存在：

~~~text
%LOCALAPPDATA%\GPT-DeepSeek\state
~~~

API Key 仍从 Windows 环境变量读取，不会写入状态目录。

## 常见问题

### 双击没有反应

确认完整解压了 ZIP，而不是直接在压缩包预览中运行。检查
`GPT-DeepSeek-CLI.exe` 和 `_internal` 是否仍在主程序旁边。

### API 显示不可用

补齐 `GPT_API_KEY`、`GPT_API_BASE`、`GPT_MODEL`，然后完全退出并重新打开
程序。启动检查只确认配置是否齐全；真实连接会在执行任务时验证。

### Harness 显示不可用

确认 DeepSeek 环境变量已配置，并在新的 PowerShell 中运行
`dsh --version`。如果命令找不到，请把 Harness launcher 加入 `PATH`。

### Workspace 显示无效

请选择包含 `.git` 的 Git 仓库根目录。普通文件夹不能作为执行 Workspace。

### 如何卸载

退出程序后删除解压目录即可。若也要删除本地任务状态，可手动删除
`%LOCALAPPDATA%\GPT-DeepSeek\state`；该操作无法恢复历史状态。

## 开发者构建

源码构建步骤见 [Windows packaging](../packaging/README.md)。构建产生的
`build/` 和 `dist/` 仅用于本地验证，不提交到 Git。

# Provider Setup

This guide prepares the existing V1 orchestrator for a real provider run. The
planner and reviewer use an OpenAI-compatible HTTP API. The executor uses the
DeepSeek Harness (`dsh`). No API key belongs in source code, Git, task state, or
logs.

## Environment file

Copy `.env.example` to `.env` and fill in the values below. The orchestrator
CLI reads exported environment variables. The included smoke test also reads
the local `.env` file for convenience; it never writes it.

```powershell
Copy-Item .env.example .env
```

`.env` is ignored by Git. Keep it local or use a secrets manager in CI.

The orchestrator itself reads the process environment rather than parsing
`.env`. In PowerShell, load the local values for the current terminal before a
real run (the command does not print them):

```powershell
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
    Set-Item -Path "Env:$($matches[1].Trim())" -Value $matches[2].Trim()
  }
}
```

## GPT Provider

Set these variables for the planner and reviewer:

```env
GPT_API_KEY=your_key
GPT_API_BASE=https://your-provider/v1
GPT_MODEL=your-model
```

`GPT_API_BASE` may point to OpenAI's official API, an OpenAI-compatible service,
or an enterprise proxy. Use the base URL exposed by that service; the adapter
adds `/chat/completions` when the URL does not already include it. Do not assume
one fixed endpoint for every provider.

## DeepSeek Provider

Set these variables for the executor and its Harness environment:

```env
DEEPSEEK_API_KEY=your_key
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=your-model
```

The orchestrator maps `DEEPSEEK_API_BASE` to the Harness-compatible
`DEEPSEEK_BASE_URL` when needed. Use the endpoint and model name supplied by
your DeepSeek account or approved gateway.

Optional workflow setting:

```env
MAX_REVIEW_ITERATIONS=3
```

The current V1 default is `3`; change it only for a deliberate validation run.

## Install and check dsh

The official package can be attempted with:

```powershell
npx @deepseek-ai/dsh web
```

If the published package reports a missing `@deepseek-ai/dsh-app-boot`
dependency, use the checked-in upstream source checkout:

```powershell
pnpm install --frozen-lockfile
pnpm run build
pnpm dsh --version
```

Run those commands from `work/upstream/deepseek-harness`. The prepared source
checkout currently reports `0.1.6-alpha.1`. To make the smoke test use a custom
command, set `DSH_COMMAND`, for example:

```powershell
$env:DSH_COMMAND = 'pnpm --dir work/upstream/deepseek-harness dsh'
```

For the orchestrator's default `dsh` executable name, install the Harness so
that `dsh` is on `PATH`, or expose a local launcher that forwards to the source
checkout. The provider adapter keeps the documented `dsh` command.

## Provider Smoke Test

From the repository root, run:

```powershell
python scripts/provider_smoke_test.py
```

The test checks configuration, sends one minimal chat completion to each
configured provider, and runs `dsh --version`. It reports `PASS` or `FAILED`
with a reason. It does not print keys, response bodies, prompts, or local file
contents. A missing configuration is reported explicitly, for example:

```text
GPT API:
FAILED
Reason: Missing configuration: GPT_API_KEY, GPT_API_BASE, GPT_MODEL
```

An HTTP failure is reported without the provider response body. Fix the stated
endpoint, model, network, or credential issue and run the test again.

## Required user action

Before V1.1 Real Provider Validation, configure:

```text
GPT_API_KEY
GPT_API_BASE
GPT_MODEL
DEEPSEEK_API_KEY
DEEPSEEK_API_BASE
DEEPSEEK_MODEL
```

Then run the smoke test and retain its result for the validation evidence chain.
Do not commit `.env` or paste its contents into issues, logs, or task reports.

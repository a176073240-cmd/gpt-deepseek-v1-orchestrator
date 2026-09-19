# Providers

GPT-DeepSeek V1 Orchestrator supports OpenAI-compatible chat-completions APIs for the GPT Planner and GPT Reviewer. Provider-specific model names, base URLs, quotas, pricing, data handling, and availability are controlled by the provider you choose.

## Compatibility

A provider must expose an OpenAI-compatible POST /chat/completions endpoint and accept the configured model and bearer credential. Configure:

- GPT_API_KEY
- GPT_API_BASE
- GPT_MODEL

GPT_API_BASE may be a provider base URL or the full /chat/completions endpoint. The CLI reads process environment variables and does not load .env automatically. Use a shell, secret manager, CI secret store, or dotenv launcher, and never commit credentials.

DeepSeek Harness execution has its own provider settings:

- DEEPSEEK_API_KEY
- DEEPSEEK_API_BASE
- DEEPSEEK_MODEL
- DSH_COMMAND when a source checkout needs an explicit launcher

See [Provider Setup](provider-setup.md) for shell examples and the smoke-test procedure.

## Author-tested Provider: Modelflare

The project author has tested an OpenAI-compatible configuration with [Modelflare](https://modelflare.dev/sign-up?partner=IEQJUO5IKYU8).

Modelflare is a third-party service. It is not maintained by this project, DeepSeek, or OpenAI, and its inclusion here does not represent an official partnership or endorsement. The sign-up URL contains a partner identifier. Review the provider's current terms, privacy policy, model availability, pricing, and data-retention practices before use.

You are not required to use Modelflare. Any provider that satisfies the compatible endpoint and response requirements may be substituted by changing GPT_API_BASE, GPT_API_KEY, and GPT_MODEL.

## Provider-neutral Example

~~~powershell
$env:GPT_API_KEY = "<set-in-your-secret-manager>"
$env:GPT_API_BASE = "https://provider.example/v1"
$env:GPT_MODEL = "provider-model-name"

$env:DEEPSEEK_API_KEY = "<set-in-your-secret-manager>"
$env:DEEPSEEK_API_BASE = "https://provider.example/v1"
$env:DEEPSEEK_MODEL = "deepseek-model-name"
~~~

The placeholders above are not working credentials. Do not paste real keys into documentation, task contracts, committed files, state files, logs, or issue reports.

## Switching Providers

1. Confirm that the replacement implements the OpenAI-compatible chat-completions request and response shape.
2. Choose a model that supports the required context and JSON-oriented prompting.
3. Update only the environment variables for the planner/reviewer or Harness side being replaced.
4. Run the provider smoke test described in [Provider Setup](provider-setup.md).
5. Run an offline FakeAdapter test separately to distinguish orchestration problems from provider or network problems.

Provider behavior can change independently of this repository. Treat rate limits, output formats, model aliases, and service policies as external dependencies.

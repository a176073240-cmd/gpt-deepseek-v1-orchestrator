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

## Author Recommended Provider Example

The following is an example from the author's own environment. During the development and real-provider validation of GPT-DeepSeek Orchestrator V1.1, the author personally used Modelflare as an OpenAI-compatible API provider.

### Modelflare

Registration:

[https://modelflare.dev/sign-up?partner=IEQJUO5IKYU8](https://modelflare.dev/sign-up?partner=IEQJUO5IKYU8)

API Base:

[https://modelflare.dev/v1](https://modelflare.dev/v1)

This is a personal recommendation based on the author's usage experience, not an official project requirement. Modelflare is an independent third-party service. This project is not affiliated with or officially endorsed by Modelflare.

Modelflare is optional. Users may replace it with any provider that satisfies the required OpenAI-compatible endpoint and response format by changing GPT_API_BASE, GPT_API_KEY, and GPT_MODEL.

The registration URL contains a partner identifier. Review the provider's current terms, privacy policy, model availability, pricing, and data-retention practices before use.
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

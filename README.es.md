# GPT-DeepSeek V1 Orchestrator

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

> Un flujo de programación persistente que combina la planificación y revisión de GPT con la ejecución de DeepSeek Harness.

GPT-DeepSeek V1 Orchestrator convierte un objetivo técnico en lenguaje natural en un flujo estructurado y revisable para un repositorio Git existente. Un modelo compatible con GPT planifica, DeepSeek Harness ejecuta los cambios, las comprobaciones deterministas recopilan evidencias y un Reviewer compatible con GPT devuelve PASS, REVISE o BLOCKED.

V1.1.0 incluye persistencia, reanudación, decisiones humanas y Evidence Chain. Conserva la arquitectura Planner → Executor → Reviewer de V1 y no incluye enrutamiento de modelos, planificación multiagente ni interfaz web.

## Por qué existe este proyecto

Un único paso de prompt-to-code es difícil de auditar y recuperar. Este proyecto añade una pequeña capa de orquestación:

- guarda la planificación como un TaskContract persistente;
- separa la ejecución de la revisión independiente;
- conserva la validación y la evidencia de Git;
- permite un ciclo REVISE → PASS con límite;
- reanuda el trabajo sin volver a planificar;
- pausa decisiones de política para recibir instrucciones humanas.

## Capacidades principales

- **GPT Planner** — crea un contrato con alcance, objetivos excluidos, criterios, validación, rutas permitidas y riesgos.
- **DeepSeek Harness Executor** — ejecuta el contrato mediante dsh y conserva la identidad de sesión.
- **GPT Reviewer** — evalúa la implementación y devuelve PASS, REVISE o BLOCKED.
- **Persistencia y reanudación** — guarda cada fase de forma atómica y continúa el contrato guardado.
- **Evidence Chain** — registra validación, evidencia Git, informes, revisión y respuestas humanas.
- **Límites de seguridad** — valida rutas, captura la base Git y oculta secretos configurados.
- **Modo sin conexión** — ofrece un FakeAdapter determinista sin proveedores activos.

## Architecture

~~~mermaid
flowchart LR
    U[Objetivo] --> P[GPT Planner<br/>TaskContract]
    P --> E[DeepSeek Harness<br/>Executor]
    E --> V[Validación y evidencia Git]
    V --> R[GPT Reviewer]
    R -->|REVISE| E
    R -->|PASS| C[Completado]
    R -->|BLOCKED| H[Decisión humana]
    H -->|responder y reanudar| E
    P -. checkpoint .-> S[(Atomic StateStore)]
    E -. checkpoint .-> S
    V -. checkpoint .-> S
    R -. checkpoint .-> S
~~~

Planner y Reviewer usan POST /chat/completions compatible con OpenAI. Executor invoca DeepSeek Harness en el repositorio objetivo. El estado se guarda en .orchestrator/ y Git lo ignora. Consulta [Architecture](docs/architecture.md).

## Features

- TaskContract estructurado y validado
- Ejecución headless de Harness con subprocesos limitados
- Comandos de validación y evidencia Git status/diff
- Recuperación automática REVISE → PASS con límite
- Comandos persistentes ask, answer, status y resume
- Salida JSON para automatización
- Ocultación de secretos y límites del workspace
- Pruebas deterministas con fixtures Git temporales

## Installation

Requiere Python 3.10 o posterior y Git. La ejecución real también necesita Node.js, DeepSeek Harness y un proveedor API compatible con OpenAI.

~~~bash
git clone --recurse-submodules https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator.git
cd gpt-deepseek-v1-orchestrator
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
~~~

Sigue la documentación de [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness). Consulta [Providers](docs/providers.md) y [Provider Setup](docs/provider-setup.md).

## Quick Start

Prueba sin conexión, sin credenciales ni dsh activo:

~~~bash
orchestrator run "Inspect this fixture" --workspace /path/to/git-fixture --fake --json
~~~

Sin instalar el paquete:

~~~bash
python orchestrator.py run "Inspect this fixture" --workspace /path/to/git-fixture --fake --json
~~~

## Configuration

Copia .env.example a un archivo local ignorado y proporciona variables mediante shell, gestor de secretos o dotenv. La CLI no carga .env automáticamente.

| Variable | Cuándo | Uso |
| --- | --- | --- |
| GPT_API_KEY / GPT_API_BASE / GPT_MODEL | Ejecución real | Provider compatible con OpenAI para Planner/Reviewer |
| DEEPSEEK_API_KEY / DEEPSEEK_API_BASE | Ejecución real | Provider de DeepSeek Harness |
| DEEPSEEK_MODEL | Según Provider | Modelo para Harness |
| DSH_COMMAND | Código fuente | Comando para iniciar Harness |
| MAX_REVIEW_ITERATIONS | Opcional | Máximo de revisiones, predeterminado 3 |

No incluyas en commits credenciales, archivos locales de entorno, state, sessions, logs ni resultados de ejecución.

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

Consulta [User Guide](docs/user-guide.md) y [Demo Workflow](docs/demo-workflow.md).

## Development and validation

~~~bash
python -m pytest
python -m compileall -q src orchestrator.py
~~~

Las pruebas usan fixtures Git temporales y no necesitan proveedores activos. Los recursos de validación V1.1 están en [validation/](validation/).

## Roadmap

- **V1.1.0 — publicado:** Planner, Executor, ciclo Reviewer, reanudación, Evidence Chain, guías, demo y archivo de validación.
- **V1.2-A — en curso:** README multilingüe, proveedores, atribución, claridad de licencia y presentación de GitHub.
- **Futuro:** mejoras de empaquetado, ejemplos de proveedores, automatización CI/releases y observabilidad opcional. No son funciones actuales.

## License

El código y la documentación originales usan [Apache License 2.0](LICENSE).

## Patent Notice

Apache-2.0 Section 3 concede una licencia de patentes de cada Contributor para las reivindicaciones que puede licenciar y que su Contribution infringe necesariamente sola o junto con el Work. Se aplican las condiciones, incluida la terminación por litigio de patentes. Este resumen no añade licencia ni garantía; prevalece [LICENSE](LICENSE).

## Third-party Attribution

DeepSeek Harness, Augani Agent Orchestrator y otros componentes fijados mantienen sus licencias MIT y no se relicencian bajo Apache-2.0. Consulta [Third-party Attribution](docs/third-party.md).

## Documentation

[User Guide](docs/user-guide.md) · [Demo Workflow](docs/demo-workflow.md) · [Architecture](docs/architecture.md) · [Providers](docs/providers.md) · [Provider Setup](docs/provider-setup.md) · [Third-party Attribution](docs/third-party.md) · [Contributing](CONTRIBUTING.md)

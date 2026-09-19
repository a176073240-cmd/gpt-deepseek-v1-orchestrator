# GPT-DeepSeek V1 Orchestrator

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

> GPT 계획·검토와 DeepSeek Harness 실행을 결합한 지속 가능한 코딩 워크플로입니다.

**목표와 Git 저장소를 제공하면 TaskContract 생성, DeepSeek Harness 실행, 변경 검증, 독립 Reviewer의 통과·수정·중단 판단까지 수행합니다.**

GPT-DeepSeek V1 Orchestrator는 자연어 개발 목표를 기존 Git 저장소를 위한 구조화되고 검토 가능한 워크플로로 변환합니다. GPT 호환 모델이 계획하고, DeepSeek Harness가 변경을 실행하며, 결정적 검사가 증거를 수집하고, GPT 호환 Reviewer가 PASS, REVISE 또는 BLOCKED를 반환합니다.

V1.1.0은 영속성, 재개, 사람의 결정, Evidence Chain을 제공합니다. V1의 Planner → Executor → Reviewer 구조를 유지하며 모델 라우팅, 멀티 에이전트 스케줄링, Web UI는 포함하지 않습니다.

## 이 프로젝트가 필요한 이유

한 번의 prompt-to-code 단계는 감사와 복구가 어렵습니다. 이 프로젝트는 작은 오케스트레이션 계층을 추가합니다.

- 계획을 영속적인 TaskContract로 저장
- 실행과 독립 검토를 분리
- 검증 결과와 Git 증거를 작업에 보존
- 제한된 REVISE → PASS 반복
- 재계획 없이 중단된 작업 재개
- 정책 결정을 위해 명시적인 사용자 입력 대기

## 핵심 기능

- **GPT Planner** — 범위, 비목표, 승인 기준, 검증, 허용 경로와 위험을 포함한 계약 생성.
- **DeepSeek Harness Executor** — dsh로 대상 Git 작업 공간에서 계약을 실행하고 세션 ID 보존.
- **GPT Reviewer** — 구현과 증거를 평가하여 PASS, REVISE 또는 BLOCKED 반환.
- **영속성과 재개** — 각 단계를 원자적으로 저장하고 저장된 계약에서 재개.
- **Evidence Chain** — 검증, Git 증거, 실행 보고서, 검토 피드백과 사용자 답변 기록.
- **안전 경계** — 경로 검사, Git 기준선 캡처, 설정된 비밀 값 마스킹.
- **오프라인 모드** — 라이브 Provider 없이 결정적 FakeAdapter로 테스트.

## Architecture

~~~mermaid
flowchart LR
    U[사용자 목표] --> P[GPT Planner<br/>TaskContract]
    P --> E[DeepSeek Harness<br/>Executor]
    E --> V[검증과 Git 증거]
    V --> R[GPT Reviewer]
    R -->|REVISE| E
    R -->|PASS| C[완료]
    R -->|BLOCKED| H[사용자 결정]
    H -->|답변 후 재개| E
    P -. checkpoint .-> S[(Atomic StateStore)]
    E -. checkpoint .-> S
    V -. checkpoint .-> S
    R -. checkpoint .-> S
~~~

Planner와 Reviewer는 OpenAI 호환 POST /chat/completions를 사용합니다. Executor는 대상 저장소에서 DeepSeek Harness를 호출합니다. 상태는 .orchestrator/에 저장되고 Git에서 제외됩니다. 자세한 내용은 [Architecture](docs/architecture.md)를 참조하세요.

## Features

- 구조화되고 검증된 TaskContract
- 제한된 하위 프로세스를 이용한 Headless Harness 실행
- 검증 명령과 Git status/diff 증거
- 반복 제한이 있는 자동 REVISE → PASS
- 영속적인 ask, answer, status, resume 명령
- 자동화를 위한 JSON 출력
- 비밀 값 마스킹과 작업 공간 경계 검사
- 임시 Git fixture를 사용하는 결정적 테스트

## Installation

요구 사항은 Python 3.10 이상과 Git입니다. 실제 실행에는 Node.js, DeepSeek Harness, OpenAI 호환 API Provider도 필요합니다.

~~~bash
git clone --recurse-submodules https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator.git
cd gpt-deepseek-v1-orchestrator
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
~~~

소스 환경은 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)를 참조하세요. Provider 설정은 [Providers](docs/providers.md)와 [Provider Setup](docs/provider-setup.md)에 있습니다.

## Quick Start

Provider 자격 증명과 라이브 dsh가 필요 없는 오프라인 테스트:

~~~bash
orchestrator run "Inspect this fixture" --workspace /path/to/git-fixture --fake --json
~~~

패키지를 설치하지 않았다면:

~~~bash
python orchestrator.py run "Inspect this fixture" --workspace /path/to/git-fixture --fake --json
~~~

## Configuration

.env.example을 로컬 제외 파일로 복사하고 shell, secret manager 또는 dotenv 도구로 환경 변수를 제공합니다. CLI는 .env를 자동으로 읽지 않습니다.

| 변수 | 필요한 경우 | 용도 |
| --- | --- | --- |
| GPT_API_KEY / GPT_API_BASE / GPT_MODEL | 실제 실행 | Planner/Reviewer의 OpenAI 호환 Provider |
| DEEPSEEK_API_KEY / DEEPSEEK_API_BASE | 실제 실행 | DeepSeek Harness Provider |
| DEEPSEEK_MODEL | Provider별 | Harness 모델 |
| DSH_COMMAND | 소스 설정 | Harness 실행 명령 |
| MAX_REVIEW_ITERATIONS | 선택 | 최대 검토/수정 횟수, 기본값 3 |

자격 증명, 로컬 환경 파일, state, sessions, logs 또는 런타임 출력을 커밋하지 마세요.

## 작성자 추천 API 설정

GPT-DeepSeek Orchestrator의 개발 및 실제 Provider 검증 과정에서 작성자는 다음 OpenAI-compatible API Provider를 직접 사용했습니다.

### Modelflare

등록:

[https://modelflare.dev/sign-up?partner=IEQJUO5IKYU8](https://modelflare.dev/sign-up?partner=IEQJUO5IKYU8)

API Base:

[https://modelflare.dev/v1](https://modelflare.dev/v1)

- V1.1 개발 및 검증 중 작성자가 직접 사용
- OpenAI-style API 인터페이스와 호환
- GPT Planner, GPT Reviewer 및 DeepSeek Provider 구성에 사용 가능

이 추천은 작성자의 개인 사용 경험을 바탕으로 합니다.

Modelflare는 독립적인 제3자 서비스입니다.

본 프로젝트는 Modelflare와 제휴하지 않았으며 공식적인 보증을 받지 않았습니다.

사용자는 다른 호환 OpenAI-compatible API Provider를 자유롭게 선택할 수 있습니다.

등록 URL에는 partner 식별자가 포함됩니다. 사용 전에 약관, 개인정보 정책, 가격, 모델 가용성, 데이터 보존 정책을 확인하세요. 일반 설정은 [Providers](docs/providers.md)를 참조하세요.
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

전체 흐름은 [User Guide](docs/user-guide.md)와 [Demo Workflow](docs/demo-workflow.md)를 참조하세요.

## Development and validation

~~~bash
python -m pytest
python -m compileall -q src orchestrator.py
~~~

테스트는 임시 Git fixture를 사용하며 라이브 Provider가 필요 없습니다. V1.1 검증 자산은 [validation/](validation/)에 있습니다.

## Roadmap

- **V1.1.0 — 출시됨:** Planner, Executor, Reviewer 반복, 재개, Evidence Chain, 가이드, 데모, 검증 아카이브.
- **V1.2-A — 진행 중:** 다국어 README, Provider 문서, 저작자 표시, 라이선스 명확화, GitHub 표시.
- **향후 후보:** 패키징 개선, Provider 예제, CI/릴리스 자동화, 선택적 관측성. 현재 기능은 아닙니다.

## License

원본 코드와 문서는 [Apache License 2.0](LICENSE)으로 배포됩니다.

## Patent Notice

Apache-2.0 Section 3은 각 Contributor가 라이선스할 수 있고 해당 Contribution 단독 또는 Work와의 결합으로 필연적으로 침해되는 특허 청구항에 대한 라이선스를 부여합니다. 특허 소송 시 종료 조항을 포함한 라이선스 조건이 적용됩니다. 이 요약은 별도 특허 권리나 보증을 추가하지 않으며 [LICENSE](LICENSE)가 우선합니다.

## Third-party Attribution

DeepSeek Harness와 Augani Agent Orchestrator 등의 고정된 제3자 소스는 각각의 MIT License를 유지하며, 본 프로젝트의 Apache-2.0으로 재라이선스되지 않습니다. [Third-party Attribution](docs/third-party.md)을 참조하세요.

## Documentation

[User Guide](docs/user-guide.md) · [Demo Workflow](docs/demo-workflow.md) · [Architecture](docs/architecture.md) · [Providers](docs/providers.md) · [Provider Setup](docs/provider-setup.md) · [Third-party Attribution](docs/third-party.md) · [Contributing](CONTRIBUTING.md)

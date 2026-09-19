# GPT-DeepSeek V1 Orchestrator

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md)

> GPT による計画・レビューと DeepSeek Harness による実行を組み合わせた、永続的なコーディングワークフローです。

GPT-DeepSeek V1 Orchestrator は、自然言語の開発目標を既存の Git リポジトリ向けの構造化・レビュー可能なワークフローへ変換します。GPT 互換モデルが計画し、DeepSeek Harness が変更を実行し、決定論的な検証が証拠を収集し、GPT 互換 Reviewer が PASS、REVISE、BLOCKED を返します。

V1.1.0 は永続化、再開、人間による判断、Evidence Chain を備えています。V1 の Planner → Executor → Reviewer 構成を維持し、モデルルーティング、マルチエージェント、Web UI は含みません。

## このプロジェクトが必要な理由

一度きりの prompt-to-code は監査と復旧が困難です。本プロジェクトは小さなオーケストレーション層を追加します。

- 計画を永続的な TaskContract として保存
- 実行と独立レビューを分離
- 検証結果と Git 証拠をタスクに保存
- 上限付き REVISE → PASS ループ
- 再計画せず中断から再開
- 方針判断のため明示的な人間入力を待機

## コア機能

- **GPT Planner** — スコープ、非目標、受入基準、検証、許可パス、リスクを含む契約を作成。
- **DeepSeek Harness Executor** — dsh で対象 Git ワークスペースを実行し、セッション ID を保持。
- **GPT Reviewer** — 実装と証拠を評価し、PASS、REVISE、BLOCKED を返却。
- **永続化と再開** — 各フェーズを原子的に保存し、保存済み契約から再開。
- **Evidence Chain** — 検証、Git 証拠、実行報告、レビュー、人間の回答を記録。
- **安全境界** — パス検査、Git ベースライン、設定済み秘密値のマスキング。
- **オフラインモード** — ライブ Provider 不要の決定論的 FakeAdapter。

## Architecture

~~~mermaid
flowchart LR
    U[ユーザー目標] --> P[GPT Planner<br/>TaskContract]
    P --> E[DeepSeek Harness<br/>Executor]
    E --> V[検証と Git 証拠]
    V --> R[GPT Reviewer]
    R -->|REVISE| E
    R -->|PASS| C[完了]
    R -->|BLOCKED| H[人間の判断]
    H -->|回答して再開| E
    P -. checkpoint .-> S[(Atomic StateStore)]
    E -. checkpoint .-> S
    V -. checkpoint .-> S
    R -. checkpoint .-> S
~~~

Planner と Reviewer は OpenAI 互換 POST /chat/completions を使用します。Executor は対象リポジトリで DeepSeek Harness を呼び出します。状態は .orchestrator/ に保存され Git から除外されます。詳細は [Architecture](docs/architecture.md)。

## Features

- 検証済みの構造化 TaskContract
- 有界サブプロセスによる Headless Harness 実行
- 検証コマンドと Git status/diff 証拠
- 反復上限付き自動 REVISE → PASS
- 永続的な ask、answer、status、resume
- 自動化向け JSON 出力
- 秘密値のマスキングとワークスペース境界検査
- 一時 Git fixture を用いる決定論的テスト

## Installation

要件は Python 3.10 以上と Git です。実運用には Node.js、DeepSeek Harness、OpenAI 互換 API Provider も必要です。

~~~bash
git clone --recurse-submodules https://github.com/a176073240-cmd/gpt-deepseek-v1-orchestrator.git
cd gpt-deepseek-v1-orchestrator
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
~~~

ソース環境は [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) を参照してください。Provider は [Providers](docs/providers.md) と [Provider Setup](docs/provider-setup.md) を参照してください。

## Quick Start

Provider 認証情報やライブ dsh を使わないオフラインテスト：

~~~bash
orchestrator run "Inspect this fixture" --workspace /path/to/git-fixture --fake --json
~~~

未インストールの場合：

~~~bash
python orchestrator.py run "Inspect this fixture" --workspace /path/to/git-fixture --fake --json
~~~

## Configuration

.env.example をローカルの除外ファイルへコピーし、shell、secret manager、dotenv から環境変数を提供します。CLI は .env を自動読込しません。

| 変数 | 必要な場合 | 用途 |
| --- | --- | --- |
| GPT_API_KEY / GPT_API_BASE / GPT_MODEL | 実行時 | Planner/Reviewer の OpenAI 互換 Provider |
| DEEPSEEK_API_KEY / DEEPSEEK_API_BASE | 実行時 | DeepSeek Harness Provider |
| DEEPSEEK_MODEL | Provider 依存 | Harness のモデル |
| DSH_COMMAND | ソース環境 | Harness 起動コマンド |
| MAX_REVIEW_ITERATIONS | 任意 | 最大レビュー/修正回数（既定 3） |

認証情報、ローカル環境ファイル、state、sessions、logs、実行出力をコミットしないでください。

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

完全な手順は [User Guide](docs/user-guide.md) と [Demo Workflow](docs/demo-workflow.md) を参照してください。

## Development and validation

~~~bash
python -m pytest
python -m compileall -q src orchestrator.py
~~~

テストは一時 Git fixture を使用しライブ Provider を必要としません。V1.1 検証資産は [validation/](validation/) にあります。

## Roadmap

- **V1.1.0 — リリース済み：** Planner、Executor、Reviewer ループ、再開、Evidence Chain、ガイド、デモ、検証アーカイブ。
- **V1.2-A — 進行中：** 多言語 README、Provider 文書、帰属、ライセンス明確化、GitHub 表示。
- **将来候補：** パッケージ改善、Provider 例、CI/リリース自動化、任意の可観測性。現行機能ではありません。

## License

オリジナルのコードと文書は [Apache License 2.0](LICENSE) です。

## Patent Notice

Apache-2.0 Section 3 は、各 Contributor が許諾でき、その Contribution 単独または Work との組合せで必然的に侵害される特許クレームについてライセンスを付与します。訴訟時の終了条項を含むライセンス条件が適用されます。本説明は追加の特許許諾や保証ではなく、[LICENSE](LICENSE) が優先します。

## Third-party Attribution

DeepSeek Harness と Augani Agent Orchestrator などの固定第三者ソースは、それぞれの MIT License のままであり、本プロジェクトの Apache-2.0 で再許諾されません。詳細は [Third-party Attribution](docs/third-party.md)。

## Documentation

[User Guide](docs/user-guide.md) · [Demo Workflow](docs/demo-workflow.md) · [Architecture](docs/architecture.md) · [Providers](docs/providers.md) · [Provider Setup](docs/provider-setup.md) · [Third-party Attribution](docs/third-party.md) · [Contributing](CONTRIBUTING.md)

# Architecture

GPT-DeepSeek V1 Orchestrator coordinates a small, evidence-driven coding workflow.

```text
User Goal
    |
    v
GPT Planner
    |
    v
TaskContract
    |
    v
DeepSeek Harness Executor
    |
    v
Validation Evidence
    |
    v
GPT Reviewer
  /   |   \\
PASS REVISE BLOCKED
  |     |      |
Done  Repair  Human Escalation
```

## Components

### GPT Planner

Interprets the user goal and produces a structured `TaskContract` containing scope, non-goals, an implementation plan, acceptance criteria, and validation requirements.

### DeepSeek Executor

Uses the DeepSeek Harness to inspect the repository, modify files, execute commands, run tests, and collect execution evidence.

### GPT Reviewer

Reviews the original goal, task contract, code changes, and evidence. It returns one of `PASS`, `REVISE`, or `BLOCKED`. A `REVISE` result creates a repair task for the executor.

### Persistence

Task state, provider session identifiers, and checkpoints are persisted so an interrupted task can resume without replanning or repeating completed steps.

### Evidence Chain

Each run records the task contract, changed files, command log, Git diff summary, test results, and reviewer result. Runtime records remain local and are excluded from the public repository.

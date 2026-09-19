# Third-party Attribution

This document separates the original GPT-DeepSeek V1 Orchestrator work from third-party source recorded in the repository. It is informational; the applicable license texts control.

## Original Work

The project-specific orchestration and documentation include:

- Planner orchestration
- TaskContract
- Reviewer loop
- Persistence and resume behavior
- Evidence Chain

Unless a file states otherwise, the original project code and documentation are licensed under the repository's [Apache License 2.0](../LICENSE).

## Third-party Components

### DeepSeek Harness

- **Purpose:** execution backend used by the DeepSeek Executor through the dsh command; it provides the source CLI and execution environment.
- **Project:** [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)
- **Repository location:** work/upstream/deepseek-harness
- **License:** MIT License
- **Compliance:** use, modification, and distribution must follow the upstream MIT terms, including retention of its copyright and permission notice. The upstream license file remains with the pinned source.

DeepSeek Harness is an independent third-party project. Its inclusion does not imply endorsement, sponsorship, or an official partnership with this repository.

### Augani Agent Orchestrator

- **Purpose:** pinned upstream reference source retained in the repository; it is not presented as original work of this project.
- **Project:** [Augani/agent-orchestrator](https://github.com/Augani/agent-orchestrator)
- **Repository location:** work/upstream/agent-orchestrator
- **License:** MIT License
- **Compliance:** use, modification, and distribution must follow the upstream MIT terms, including retention of its copyright and permission notice.

## License Boundaries

The root Apache-2.0 license applies to the original project work. It does not replace the licenses of third-party components. Each third-party component remains governed by its own license and notices. When redistributing a combined checkout or derived package, preserve all notices required by those licenses and review whether additional transitive components require attribution.

For the exact pinned source and license text, initialize the Git submodules and inspect each component's LICENSE file.

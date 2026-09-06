# CCU CLI Agent Instructions

CCU CLI is a Python command-line client for Homematic CCU systems. It uses
`hahomematic` (formerly aiohomematic) for CCU communication.

## Work routing

Read [`docs/agent-development-reference.md`](docs/agent-development-reference.md)
when changing CCU integration, CLI behavior, configuration, packaging, or tests.
It contains the local hahomematic documentation map, test boundaries, commands,
and Python CLI conventions. Do not load it for unrelated prose-only work.

Behavior changes follow test-driven development. Tests must exercise observable
behavior at the external boundary: mock the CCU backend, invoke Click commands
with `CliRunner`, use temporary config, and use `httpx.MockTransport` for ReGa
HTTP. Do not test hahomematic itself or build full mock servers.

All source, identifiers, comments, logs, configuration, and technical
documentation are English. Do not add emoji; localized user-facing strings and
representative data are exceptions when the product requires them.

## Tracking and delivery

Use `bd` for task tracking and `bd prime` for current commands. Do not create a
second task list. The single assigned delivery owner runs
`ccore session-close`; contributors do not independently close, sync, merge,
clean up, or push unless explicitly assigned delivery ownership. Stage only
files owned by the current assignment.

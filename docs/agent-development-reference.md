# Agent Development Reference

Load this document when changing CCU communication, CLI behavior, configuration,
or tests. Repository-wide workflow rules remain in [`../AGENTS.md`](../AGENTS.md).

## hahomematic documentation

CCU communication uses
[hahomematic](https://github.com/SukramJ/hahomematic), formerly aiohomematic.
Local documentation is under `llms/aiohomematic/`:

- `getting_started.md`: basic usage
- `architecture.md`: component relationships
- `common_operations.md`: frequent operations
- `data_flow.md`: data movement
- `event_bus.md`: event patterns
- `glossary.md`: terminology

Read the relevant pages before changing hahomematic integration. Refresh them
with `./llms/sync.sh`.

## Test boundaries

Use test-driven development for behavior changes: establish a failing focused
test, implement the behavior, then refactor with the test green.

| Layer | Test boundary |
|---|---|
| `CCUBackend` | mock the external backend with `unittest.mock` |
| CLI | invoke commands with `click.testing.CliRunner`; mock `get_backend` |
| Configuration | temporary files plus `monkeypatch` and `tmp_path` |
| ReGa HTTP | `httpx.MockTransport`; do not create a full mock server |

Test observable behavior, not library behavior or internal implementation
details.

```bash
uv run pytest
uv run pytest -v
uv run pytest tests/test_cli.py
uv run pytest -k "test_devices"
```

Toolchain declarations (setup actions, `requires-python`) follow the vendored
toolchains standard. CI's `toolchains` job runs the check on every push to
`main` and every pull request; that is the check that always runs. A pre-push
run happens only on hosts whose global pre-push hook calls
`scripts/dev/preflight.sh`; the repository ships no hook of its own.
`tests/test_toolchains.py` runs the check offline with uv's latest version
overridden above any real release, so it fails on any declaration that is not
`ok`, including every explicit uv version pin; Python lookups are not
overridden. Run it manually with:

```bash
python3 .agents/standards/toolchains/scripts/check_toolchain_versions.py
bash scripts/dev/preflight.sh
```

## Python CLI conventions

This is a user-invoked Python CLI. Keep the `src/` layout. Configuration resolves
from environment, then configured key command, then an explicit setup hint.
Versioning is release/tag driven rather than duplicated manually. Do not
self-update; show an upgrade command. Explicitly include non-Python package data
in the build configuration.

# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## aiohomematic Documentation

This project uses [aiohomematic](https://github.com/danielperna84/hahomematic) as the backend library for CCU communication. Local documentation is synced to `llms/aiohomematic/` for agent context.

**Key docs:**
- `llms/aiohomematic/getting_started.md` - Basic usage patterns
- `llms/aiohomematic/architecture.md` - Component relationships
- `llms/aiohomematic/common_operations.md` - Frequent use cases
- `llms/aiohomematic/data_flow.md` - How data moves through the system
- `llms/aiohomematic/event_bus.md` - Event-driven programming patterns
- `llms/aiohomematic/glossary.md` - Terminology reference

**To update docs:** `./llms/sync.sh`

Read these docs before implementing features that interact with aiohomematic.

## Testing Strategy: Test-Driven Development

**This project follows TDD. Write tests BEFORE implementing code.**

### Workflow for New Features/Changes

1. **Write failing test(s) first** - Define expected behavior
2. **Run tests to confirm they fail** - Validates test is meaningful
3. **Implement the code** - Make tests pass
4. **Refactor if needed** - Keep tests green

### Test Stack

| Layer | Approach | Tools |
|-------|----------|-------|
| `CCUBackend` | Mock backend | `unittest.mock` |
| CLI commands | Invoke CLI, mock backend | `click.testing.CliRunner` |
| Config | Temp files, env vars | `monkeypatch`, `tmp_path` |
| ReGa | Mock HTTP responses | `httpx.MockTransport` |

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_cli.py          # CLI commands via CliRunner
├── test_config.py       # Config loading
├── test_rega.py         # ReGa client tests
└── test_xmlrpc.py       # XML-RPC client tests
```

### Key Patterns

**Mocking the backend:**
```python
from unittest.mock import MagicMock
from ccu_cli.backend import Device

def test_devices_command(mocker):
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.list_devices.return_value = [
        Device(address="NEQ123", name="Switch", model="HmIP-PSM", ...)
    ]
    mocker.patch("ccu_cli.cli.get_backend", return_value=mock)

    runner = CliRunner()
    result = runner.invoke(main, ["devices"])
    assert result.exit_code == 0
```

**Testing CLI commands:**
```python
from click.testing import CliRunner
from ccu_cli.cli import main

def test_devices_command(mocker):
    mocker.patch("ccu_cli.cli.get_backend", return_value=mock_backend)
    runner = CliRunner()
    result = runner.invoke(main, ["devices"])
    assert result.exit_code == 0
```

### Running Tests

```bash
uv run pytest                    # All tests
uv run pytest -v                 # Verbose
uv run pytest tests/test_cli.py  # Specific file
uv run pytest -k "test_devices"  # Pattern match
```

### What NOT to Test

- Don't mock internal implementation details
- Don't test library behavior
- Don't create full mock servers (MockTransport is sufficient for HTTP)

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

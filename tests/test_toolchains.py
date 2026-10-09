"""Tests for repository toolchain declarations against the toolchains standard."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER = REPO_ROOT / ".agents/standards/toolchains/scripts/check_toolchain_versions.py"


def test_every_toolchain_declaration_follows_the_standard():
    # The uv override keeps the check offline. It sits above any real uv
    # release, so every explicit uv pin counts as outdated and fails the test,
    # while `version: latest` stays `ok` without a lookup.
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--root",
            str(REPO_ROOT),
            "--latest-version",
            "uv=999.0.0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    declarations = report["data"]["declarations"]
    assert declarations
    not_ok = [d for d in declarations if d["status"] != "ok"]
    assert not_ok == []

#!/usr/bin/env bash
# Pre-push preflight, run by the global pre-push hook when present.
# Pre-push arguments are ignored.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
python3 .agents/standards/toolchains/scripts/check_toolchain_versions.py

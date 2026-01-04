#!/bin/bash
set -e

BASE="https://raw.githubusercontent.com/SukramJ/hahomematic/devel/docs"
DIR="$(dirname "$0")/aiohomematic"
mkdir -p "$DIR"

echo "Syncing aiohomematic docs..."

curl -sf "$BASE/getting_started.md" > "$DIR/getting_started.md"
curl -sf "$BASE/architecture.md" > "$DIR/architecture.md"
curl -sf "$BASE/common_operations.md" > "$DIR/common_operations.md"
curl -sf "$BASE/data_flow.md" > "$DIR/data_flow.md"
curl -sf "$BASE/event_bus.md" > "$DIR/event_bus.md"
curl -sf "$BASE/glossary.md" > "$DIR/glossary.md"

echo "Done. Synced 6 docs to $DIR"

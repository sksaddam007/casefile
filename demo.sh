#!/usr/bin/env bash
# CaseFile demo reset + run: fresh graph, then a full investigation.
set -euo pipefail
cd "$(dirname "$0")"

echo "── resetting FalkorDB graph (docker: casefile-falkordb) ──"
docker exec casefile-falkordb redis-cli -p 6379 GRAPH.DELETE bank >/dev/null 2>&1 || true
uv run python -m casefile.loader | tail -n 15

echo "── running CaseFile ──"
if [[ "${CASEFILE_MOCK:-0}" == "1" ]]; then
  uv run python -m casefile.mock_agent
else
  uv run python -m casefile.agent
fi

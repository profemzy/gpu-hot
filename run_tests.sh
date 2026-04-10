#!/usr/bin/env bash
set -euo pipefail

echo "=== gpu-hot Unit Tests ==="
echo "Building test container..."

docker compose -f tests/docker-compose.unittest.yml build

echo "Running tests..."
docker compose -f tests/docker-compose.unittest.yml run --rm unittest

echo "=== Tests Complete ==="

#!/usr/bin/env bash
set -euo pipefail

# Get version from git tag or describe
if git describe --tags --exact-match 2>/dev/null; then
    exit 0
fi

git describe --tags --always 2>/dev/null || echo "dev"

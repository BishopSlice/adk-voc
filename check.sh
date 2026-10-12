#!/bin/sh
set -e
cd "$(dirname "$0")"
ruff check .
python3 -m pytest -q tests/

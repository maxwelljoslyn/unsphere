#!/bin/bash
set -euo pipefail
cd /home/maxwell/unsphere/ && git pull && uv sync && uv run manage.py migrate && uv run manage.py collectstatic --noinput && sudo systemctl restart unsphere

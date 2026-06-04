#!/bin/bash
set -euo pipefail
git pull
uv sync
uv run manage.py migrate
uv run manage.py collectstatic --noinput
sudo systemctl restart parrot

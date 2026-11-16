#!/usr/bin/env bash
set -euo pipefail

APP=/srv/asoundjob

if [ "$(id -u)" -ne 0 ]; then
	echo "run with sudo" >&2
	exit 1
fi

as_app() {
	sudo -u asoundjob -H bash -c "set -euo pipefail; cd $APP; set -a; . /etc/asoundjob/asoundjob.env; set +a; $1"
}

echo "== saving admin company edits"
as_app "deploy/seed-push.sh"

echo "== pulling code"
as_app "git pull --ff-only origin main"

echo "== python packages"
as_app "uv pip install --quiet --python venv/bin/python -r requirements.txt"

echo "== database migrations"
as_app "cd scraper && ../venv/bin/alembic upgrade head"

echo "== building the website"
as_app "cd web && npm ci --no-audit --no-fund --loglevel=error && npm run build"

echo "== restarting"
cp "$APP"/deploy/systemd/*.service "$APP"/deploy/systemd/*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl restart asoundjob-api asoundjob-web
sleep 3
systemctl --no-pager --lines=0 status asoundjob-api asoundjob-web | grep -E "Loaded|Active"
echo "== done"

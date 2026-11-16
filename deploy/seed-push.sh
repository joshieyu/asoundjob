#!/usr/bin/env bash
set -euo pipefail

cd /srv/asoundjob
SEED=data/audio_companies_final.json

if git diff --quiet -- "$SEED"; then
	echo "no company edits to push"
	exit 0
fi

git add -- "$SEED"
git -c user.name="ASoundJob server" -c user.email="server@asoundjob.com" \
	commit -q -m "Company edits from the admin panel ($(date -u +%Y-%m-%d))"
git pull -q --rebase origin main
git push -q origin HEAD:main
echo "pushed company edits"

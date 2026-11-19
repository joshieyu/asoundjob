#!/usr/bin/env bash
set -euo pipefail

cd /srv/asoundjob
SEED=data/audio_companies_final.json

if git diff --quiet -- "$SEED"; then
	echo "no company edits to push"
	exit 0
fi

export GIT_AUTHOR_NAME="ASoundJob server" GIT_AUTHOR_EMAIL="server@asoundjob.com"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

git add -- "$SEED"
git commit -q -m "Company edits from the admin panel ($(date -u +%Y-%m-%d))"
git pull -q --rebase origin main
git push -q origin HEAD:main
echo "pushed company edits"

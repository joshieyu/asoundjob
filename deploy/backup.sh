#!/usr/bin/env bash
set -euo pipefail

DB=/var/lib/asoundjob/asoundjob.db
DIR=/var/lib/asoundjob/backups
KEEP=14

mkdir -p "$DIR"
target="$DIR/asoundjob-$(date +%Y-%m-%d).db"
sqlite3 "$DB" ".backup '$target'"
gzip -f "$target"
ls -1t "$DIR"/asoundjob-*.db.gz | tail -n +$((KEEP + 1)) | xargs -r rm --
echo "backup written: $target.gz"

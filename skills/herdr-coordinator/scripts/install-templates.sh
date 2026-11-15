#!/bin/sh
# Install this skill's hc worker templates into herdr-core's template folder.
# Missing → copied. Same → left. Different → kept (yours), unless --force.
# Usage: sh install-templates.sh [--force]
set -eu
src="$(cd "$(dirname "$0")/../templates" && pwd)"
dst="${XDG_CONFIG_HOME:-$HOME/.config}/herdr-core/templates"
mkdir -p "$dst"
for f in "$src"/*.md; do
  name=$(basename "$f")
  if [ ! -e "$dst/$name" ]; then
    cp "$f" "$dst/$name"; echo "installed $name"
  elif cmp -s "$f" "$dst/$name"; then
    echo "up to date $name"
  elif [ "${1:-}" = "--force" ]; then
    rm -f "$dst/$name"; cp "$f" "$dst/$name"; echo "replaced $name"
  else
    echo "differs $name (kept yours; --force to replace)"
  fi
done

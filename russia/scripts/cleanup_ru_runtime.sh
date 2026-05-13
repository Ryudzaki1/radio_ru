#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/opt/radio_ru}"
OLD_DIR="${OLD_DIR:-/opt/ai-chill-radio}"

if [ ! -d "$APP_DIR" ]; then
  echo "APP_DIR missing: $APP_DIR" >&2
  exit 1
fi

cd "$APP_DIR"

if [ -f .env ]; then
  before="$(grep -c '^PORT=' .env || true)"
  backup=".env.bak-dedupe-$(date +%Y%m%d%H%M%S)"
  cp -a .env "$backup"
  awk -F= '
    /^[A-Za-z_][A-Za-z0-9_]*=/ {
      if (seen[$1]++) next
    }
    { print }
  ' .env > .env.dedup
  mv .env.dedup .env
  chmod 600 .env
  after="$(grep -c '^PORT=' .env || true)"
  echo "PORT_BEFORE=$before"
  echo "PORT_AFTER=$after"
  echo "ENV_BACKUP=$APP_DIR/$backup"
fi

if [ -e "$OLD_DIR" ]; then
  resolved="$(readlink -f "$OLD_DIR")"
  if [ "$resolved" != "/opt/ai-chill-radio" ]; then
    echo "Refusing to remove unexpected path: $resolved" >&2
    exit 1
  fi
  rm -rf "$OLD_DIR"
  echo "REMOVED_OLD_DIR=$OLD_DIR"
else
  echo "OLD_DIR_ABSENT=$OLD_DIR"
fi

#!/usr/bin/env bash
# Serve the MPL Season 7 site + Pages Functions + a throwaway local D1 database.
#
#   APP_DIR=../mpl-season7 ./scripts/run_local_app.sh          # foreground
#   APP_DIR=../mpl-season7 ./scripts/run_local_app.sh --detach # background, waits for health
#
# The database lives in $APP_DIR/.wrangler/state and is recreated on every run, so test data
# never accumulates and production (Cloudflare D1) is never touched.
set -euo pipefail

APP_DIR="${APP_DIR:-.app}"
PORT="${PORT:-8788}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-qa-admin-pass}"
WRANGLER_VERSION="${WRANGLER_VERSION:-4.167.0}"
LOG_FILE="${LOG_FILE:-wrangler.log}"

if [[ ! -f "$APP_DIR/schema.sql" ]]; then
  echo "error: $APP_DIR does not look like the mpl-season7 app (schema.sql missing)" >&2
  exit 1
fi

cd "$APP_DIR"
wrangler() { npx --yes "wrangler@${WRANGLER_VERSION}" "$@"; }

rm -rf .wrangler/state
wrangler d1 execute DB --local --file schema.sql >/dev/null

# Local-only secrets. .dev.vars is git-ignored by the app repo.
cat > .dev.vars <<VARS
ADMIN_PASSWORD=${ADMIN_PASSWORD}
SESSION_SECRET=$(head -c 32 /dev/urandom | base64 | tr -d '\n')
VARS

args=(pages dev . --ip 127.0.0.1 --port "$PORT" --binding MPL_ENV=test --show-interactive-dev-session=false)

if [[ "${1:-}" != "--detach" ]]; then
  exec npx --yes "wrangler@${WRANGLER_VERSION}" "${args[@]}"
fi

nohup npx --yes "wrangler@${WRANGLER_VERSION}" "${args[@]}" >"$LOG_FILE" 2>&1 &
echo $! > .wrangler-pid
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    echo "app ready on http://127.0.0.1:${PORT}"
    exit 0
  fi
  sleep 1
done
echo "error: app did not become healthy; last log lines:" >&2
tail -n 40 "$LOG_FILE" >&2
exit 1

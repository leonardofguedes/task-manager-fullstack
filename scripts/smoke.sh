#!/usr/bin/env bash
# End-to-end smoke test against a running `docker compose up` stack (PostgreSQL, Redis, worker,
# nginx). Used by CI and handy before a demo: ./scripts/smoke.sh
set -euo pipefail

BASE="${BASE:-http://localhost:5173}"
API="$BASE/api/v1"

PY=$(command -v python3 >/dev/null && python3 -c "" 2>/dev/null && echo python3 || echo python)
json() { "$PY" -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

echo "waiting for $BASE/health"
for _ in $(seq 1 60); do
  [ "$(status "$BASE/health")" = 200 ] && break
  sleep 2
done
[ "$(status "$BASE/health")" = 200 ] || fail "stack did not become healthy"

login() {
  curl -sf -X POST "$API/auth/login" -d "username=$1&password=demo1234" | json 'd["access_token"]'
}
ALICE=$(login alice@example.com) || fail "demo login for alice"
BOB=$(login bob@example.com) || fail "demo login for bob"

total=$(curl -sf "$API/tasks" -H "Authorization: Bearer $ALICE" | json 'd["total"]')
[ "$total" -ge 12 ] || fail "expected the 12 seeded tasks, got $total"

[ "$(status -X POST "$API/auth/login" -d 'username=alice@example.com&password=wrong-pass')" = 401 ] \
  || fail "wrong password should be 401"
[ "$(status "$API/tasks/2147483648" -H "Authorization: Bearer $ALICE")" = 422 ] \
  || fail "id beyond PostgreSQL INTEGER should be 422"
[ "$(status "$API/tasks/999999" -H "Authorization: Bearer $ALICE")" = 404 ] \
  || fail "unknown task should be 404"

bob_id=$(curl -sf "$API/users" -H "Authorization: Bearer $ALICE" \
  | json '[u["id"] for u in d if u["email"]=="bob@example.com"][0]')
title="smoke-$(date +%s)"
[ "$(status -X POST "$API/tasks" -H "Authorization: Bearer $ALICE" -H 'Content-Type: application/json' \
  -d "{\"title\":\"$title\",\"assignee_id\":$bob_id}")" = 201 ] || fail "create assigned task"

echo "waiting for the worker to notify bob"
for _ in $(seq 1 30); do
  if curl -sf "$API/notifications" -H "Authorization: Bearer $BOB" | grep -q "$title"; then
    echo "OK: API, PostgreSQL, Redis, worker and nginx all work end to end"
    exit 0
  fi
  sleep 1
done
fail "bob was not notified about '$title'"

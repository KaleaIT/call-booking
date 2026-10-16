#!/usr/bin/env bash
#
# demo_api.sh — Calendly-style backend flow через HTTP API с проверкой кодов.
# Один пользователь (HOST) публикует слот, другой (GUEST) его бронирует.
# Завершается с кодом 0, только если все шаги прошли.
#
# Использование:
#   ./scripts/demo_api.sh
#   BASE=http://localhost:8080 ./scripts/demo_api.sh
#
# Зависимости: bash, curl, python3
set -u

BASE="${BASE:-http://localhost:8080}"

if [ -t 1 ]; then G=$'\033[32m'; R=$'\033[31m'; B=$'\033[34m'; D=$'\033[2m'; X=$'\033[0m'; else G=; R=; B=; D=; X=; fi
step()  { printf "\n${B}▶ %s${X}\n" "$1"; }
ok()    { printf "  ${G}✅ %s${X}\n" "$1"; }
die()   { printf "  ${R}❌ %s${X}\n" "$1"; exit 1; }

CODE=""; BODY=""
api() {
  local method="$1" path="$2" data="${3:-}" token="${4:-}"
  local args=(-s -m 10 -X "$method" "$BASE$path" -w $'\n%{http_code}')
  [ -n "$data" ]  && args+=(-H 'Content-Type: application/json' -d "$data")
  [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
  local resp; resp="$(curl "${args[@]}")" || die "curl не достучался до $BASE"
  CODE="${resp##*$'\n'}"; BODY="${resp%$'\n'*}"
}
expect() { [ "$CODE" = "$1" ] && ok "$2 (HTTP $CODE)" || die "$2: ожидал $1, получил $CODE${BODY:+ — $BODY}"; }
jget()   { printf '%s' "$BODY" | python3 -c "import sys,json;print(json.load(sys.stdin)$1)"; }

register_and_login() { # $1=label -> echoes "id token"
  local email="demo_${1}_$(date +%s)_$RANDOM@example.com"
  api POST /auth/register "{\"email\":\"$email\",\"password\":\"secret123\",\"full_name\":\"$1\"}"
  [ "$CODE" = 201 ] || die "register $1: $CODE $BODY"
  local uid; uid="$(jget "['id']")"
  api POST /auth/login "{\"email\":\"$email\",\"password\":\"secret123\"}"
  [ "$CODE" = 200 ] || die "login $1: $CODE $BODY"
  printf '%s %s' "$uid" "$(jget "['access_token']")"
}

echo "${D}BASE = $BASE${X}"

# ── HOST: регистрация + публикация слота ────────────────────────
step "1. HOST регистрируется, логинится, публикует слот"
read HOST_ID HOST_TOKEN <<<"$(register_and_login Host)"
ok "host id=$HOST_ID"
api POST /booking/slots '{"start_time":"2026-09-01T10:00:00Z","end_time":"2026-09-01T10:30:00Z"}' "$HOST_TOKEN"
expect 201 "host создаёт слот"
SLOT_ID="$(jget "['id']")"; ok "slot_id=$SLOT_ID"

# ── GUEST: регистрация ──────────────────────────────────────────
step "2. GUEST регистрируется и логинится"
read GUEST_ID GUEST_TOKEN <<<"$(register_and_login Guest)"
ok "guest id=$GUEST_ID"

# ── публичная страница хоста: список доступных слотов ───────────
step "3. GUEST открывает страницу HOST и видит доступные слоты (публично)"
api GET "/booking/slots?owner_id=$HOST_ID&available_only=true"
expect 200 "список слотов хоста"
printf '%s' "$BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if any(s['id']==$SLOT_ID and s['status']=='available' for s in d) else 1)" \
  && ok "слот $SLOT_ID виден и доступен" || die "слот $SLOT_ID не найден у хоста"

# ── HOST не может забронировать свой же слот ────────────────────
step "4. HOST пытается забронировать СВОЙ слот -> 400"
api POST "/booking/slots/$SLOT_ID/book" "" "$HOST_TOKEN"
expect 400 "host не бронирует свой слот"

# ── GUEST бронирует ─────────────────────────────────────────────
step "5. GUEST бронирует слот"
api POST "/booking/slots/$SLOT_ID/book" "" "$GUEST_TOKEN"
expect 201 "guest бронирует"
BOOKING_ID="$(jget "['id']")"; ok "booking_id=$BOOKING_ID"

# ── повторная бронь -> 409 ──────────────────────────────────────
step "6. Повторная бронь того же слота -> 409"
api POST "/booking/slots/$SLOT_ID/book" "" "$GUEST_TOKEN"
expect 409 "повторная бронь"
api GET "/booking/slots?owner_id=$HOST_ID&available_only=true"
printf '%s' "$BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if all(s['id']!=$SLOT_ID for s in d) else 1)" \
  && ok "слот ушёл из доступных" || die "слот всё ещё доступен после брони"

# ── GUEST отменяет ──────────────────────────────────────────────
step "7. GUEST отменяет бронь"
api POST "/booking/bookings/$BOOKING_ID/cancel" "" "$GUEST_TOKEN"
expect 200 "отмена брони"
[ "$(jget "['status']")" = "cancelled" ] && ok "status=cancelled" || die "статус не cancelled"

# ── слот снова доступен ─────────────────────────────────────────
step "8. Слот снова доступен у хоста"
api GET "/booking/slots?owner_id=$HOST_ID&available_only=true"
expect 200 "список после отмены"
printf '%s' "$BODY" | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if any(s['id']==$SLOT_ID and s['status']=='available' for s in d) else 1)" \
  && ok "слот $SLOT_ID снова доступен" || die "слот не вернулся в доступные"

printf "\n${G}════════════════════════════════════════════${X}\n"
printf "${G}  ✅ Calendly-flow пройден полностью${X}\n"
printf "${G}════════════════════════════════════════════${X}\n"

#!/usr/bin/env bash
set -euo pipefail

FRIGATE_URL="${FRIGATE_URL:-http://192.168.1.20:8971}"
KEYCHAIN_SERVICE="Frigate Home Assistant Viewer"
username="homeassistant_muse"
password="$(security find-generic-password -w -s "$KEYCHAIN_SERVICE")"
cookie_jar="$(mktemp)"
trap 'password=""; rm -f "$cookie_jar"' EXIT

login_code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --cookie-jar "$cookie_jar" --request POST \
  --header 'Content-Type: application/json' \
  --data "$(jq -cn --arg user "$username" --arg password "$password" \
    '{user: $user, password: $password}')" \
  "$FRIGATE_URL/api/login")"
[[ "$login_code" == "200" ]]

profile="$(curl --silent --show-error --fail --cookie "$cookie_jar" \
  "$FRIGATE_URL/api/profile")"
jq -e --arg user "$username" \
  '.username == $user and .role == "viewer"' >/dev/null <<<"$profile"

admin_code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --cookie "$cookie_jar" "$FRIGATE_URL/api/users")"
[[ "$admin_code" == "403" ]]

stats_code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --cookie "$cookie_jar" "$FRIGATE_URL/api/stats")"
[[ "$stats_code" == "200" ]]

echo "PASS Frigate viewer login=200 role=viewer stats=200 admin=403"

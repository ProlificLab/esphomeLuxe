#!/usr/bin/env bash
set -euo pipefail

OPNSENSE_HOST="${OPNSENSE_HOST:-root@192.168.1.1}"
OPNSENSE_URL="${OPNSENSE_URL:-https://10.10.30.1}"
KEYCHAIN_KEY_SERVICE="OPNsense Home Assistant API Key"
KEYCHAIN_SECRET_SERVICE="OPNsense Home Assistant API Secret"

api_key="$(security find-generic-password -w -s "$KEYCHAIN_KEY_SERVICE")"
api_secret="$(security find-generic-password -w -s "$KEYCHAIN_SECRET_SERVICE")"
trap 'api_key=""; api_secret=""' EXIT

payload="$(curl --silent --show-error --fail --insecure --basic \
  --user "$api_key:$api_secret" "$OPNSENSE_URL/api/muse/status/gateways")"
jq -e '.status == "ok" and (.gateways | length) > 0' >/dev/null <<<"$payload"

forbidden_code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --insecure --basic --user "$api_key:$api_secret" \
  "$OPNSENSE_URL/api/auth/user/search")"
[[ "$forbidden_code" == "403" ]]

post_code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --insecure --basic --user "$api_key:$api_secret" --request POST \
  "$OPNSENSE_URL/api/muse/status/gateways")"
[[ "$post_code" == "405" ]]

privileges="$(printf '%s\n' \
  '<?php require_once("legacy_bindings.inc");' \
  '$u=(new \OPNsense\Auth\User())->getUserByName("homeassistant_muse");' \
  'echo (string)$u->priv;' | \
  ssh -o BatchMode=yes "$OPNSENSE_HOST" /usr/local/bin/php)"
[[ "$privileges" == "page-muse-readonly" ]]

effective_masks="$(printf '%s\n' \
  '<?php require_once("legacy_bindings.inc");' \
  '$a=new \OPNsense\Core\ACL(); $m=[];' \
  'foreach($a->userUrlMasks("homeassistant_muse") as $v){$m[]=$v[0];}' \
  'sort($m); echo json_encode($m);' | \
  ssh -o BatchMode=yes "$OPNSENSE_HOST" /usr/local/bin/php)"
jq -e '. == ["api/muse/status/gateways"]' >/dev/null <<<"$effective_masks"

gateway_count="$(jq '.gateways | length' <<<"$payload")"
echo "PASS OPNsense GET-only telemetry gateways=$gateway_count masks=1 unauthorized=403 post=405"

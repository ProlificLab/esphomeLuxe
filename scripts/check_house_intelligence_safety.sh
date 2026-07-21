#!/usr/bin/env bash
set -euo pipefail

PACKAGE="${1:-home-assistant/packages/muse_house_intelligence.yaml}"

if [[ ! -f "$PACKAGE" ]]; then
  echo "House-intelligence package not found: $PACKAGE" >&2
  exit 2
fi

required_markers=(
  "credential_role: PVEAuditor"
  "controls_exposed: \"{{ false }}\""
  "binary_sensor.muse_victron_data_stale"
  "binary_sensor.muse_proxmox_data_stale"
  "binary_sensor.muse_opnsense_data_stale"
  "credential_role: page-muse-readonly"
)
for marker in "${required_markers[@]}"; do
  if ! grep -Fq "$marker" "$PACKAGE"; then
    echo "House-intelligence safety marker is missing: $marker" >&2
    exit 1
  fi
done

templated_action_pattern="^[[:space:]]*-[[:space:]]+action:[[:space:]]*[\"']?\\{\\{"
if grep -En "$templated_action_pattern" "$PACKAGE"; then
  echo "Templated service actions are forbidden in house intelligence." >&2
  exit 1
fi

while IFS= read -r line; do
  action="${line#*action:}"
  action="${action//[[:space:]]/}"
  action="${action//\"/}"
  action="${action//\'/}"
  case "$action" in
    script.muse_announce | script.muse_announce_everywhere) ;;
    *)
      echo "House-intelligence action is not allowlisted: $action" >&2
      exit 1
      ;;
  esac
done < <(grep -E '^[[:space:]]*-[[:space:]]+action:' "$PACKAGE")

echo "House-intelligence safety policy passed: read-only facts and audio only."

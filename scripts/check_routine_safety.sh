#!/usr/bin/env bash
set -euo pipefail

PACKAGE="${1:-home-assistant/packages/muse_interactive_routines.yaml}"

if [[ ! -f "$PACKAGE" ]]; then
  echo "Routine package not found: $PACKAGE" >&2
  exit 2
fi

required_markers=(
  "input_boolean.muse_routines_enabled"
  "manual_required"
  "sensor_verified"
  "logbook.log"
  "guidance_only_no_critical_actions"
)

for marker in "${required_markers[@]}"; do
  if ! grep -Fq "$marker" "$PACKAGE"; then
    echo "Routine safety marker is missing: $marker" >&2
    exit 1
  fi
done

forbidden_action_pattern='^[[:space:]]*-[[:space:]]+action:[[:space:]]+(alarm_control_panel|lock|cover|button|switch|number|select|shell_command|homeassistant)\.'
if grep -En "$forbidden_action_pattern" "$PACKAGE"; then
  echo "A critical infrastructure action was added to the routine package." >&2
  exit 1
fi

templated_action_pattern="^[[:space:]]*-[[:space:]]+action:[[:space:]]*[\"']?\\{\\{"
if grep -En "$templated_action_pattern" "$PACKAGE"; then
  echo "Templated service actions are forbidden in the routine package." >&2
  exit 1
fi

while IFS= read -r line; do
  action="${line#*action:}"
  action="${action//[[:space:]]/}"
  action="${action//\"/}"
  action="${action//\'/}"
  case "$action" in
    input_select.select_option | input_number.set_value | \
      input_text.set_value | input_datetime.set_datetime | logbook.log | \
      script.muse_announce | script.muse_announce_routine_step | \
      script.muse_start_routine | script.muse_advance_routine | \
      script.muse_pause_routine | script.muse_resume_routine | \
      script.muse_cancel_routine) ;;
    *)
      echo "Routine action is not allowlisted: $action" >&2
      exit 1
      ;;
  esac
done < <(grep -E '^[[:space:]]*-[[:space:]]+action:' "$PACKAGE")

echo "Routine safety policy passed: guidance-only actions and guards are present."

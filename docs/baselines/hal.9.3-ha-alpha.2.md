# hal.9.3-ha-alpha.2 baseline

## Scope

- Local FR-to-EN and EN-to-FR Assist pipelines.
- Canary/Whisper STT, Granite 3B translation and Piper TTS.
- Tool-free agents, one previous exchange maximum and explicit context reset.
- Ten-minute session, privacy exit, continuous-listening exit and HA restart
  recovery with deterministic pipeline restore.

## Live qualification

- Model digest matched `89962fcc...a3e5f` (Granite 3.4B Q4_K_M).
- Final FR-to-EN smoke translation: 0.993 seconds warm.
- Final EN-to-FR smoke translation: 1.556 seconds warm.
- Script start, direction swap, simulated triple-click exit, local French voice
  start, synthetic timeout and exact pipeline restore passed.
- The firmware context-reset action was exercised on exit and its counter
  reached 7 during the final end-to-end test.
- English `en_US-lessac-medium` Piper request was accepted and the Muse returned
  to `waiting`, `healthy`, with no voice error or timeout.
- Combined house narrator was restored after correcting an unbalanced Frigate
  summary template; the new static negative fixture detects that regression.

## Open gates

- Human confirmation of English pronunciation and microphone recognition in
  both directions across near/far/noisy samples.
- Verify context reset and exit using a real triple click, not only the HA
  switch simulation.
- Complete the uninterrupted 24-hour firmware endurance trace after this OTA.
- Do not promote beyond alpha until mistranslation limitations are accepted.

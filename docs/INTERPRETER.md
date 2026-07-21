# Local bounded interpreter

`hal.9.3-ha-alpha.2` adds a French-English interpreter pipeline to the Muse
Luxe. Audio stays on the LAN: Canary/Whisper performs STT, a digest-pinned
Granite 3B model translates on the Chuwi, and Piper synthesizes the target
language. The two Ollama agents have no Home Assistant tool API and cannot
control the house.

## Provisioning

```bash
PVE_HOST=root@192.168.1.10 scripts/provision_interpreter.sh
```

The provisioner creates a Home Assistant backup, validates the model digest,
creates or repairs two Ollama subentries and two Assist pipelines through the
supported APIs, publishes the package and local French intents, checks HA,
restarts it and executes the live test. It is idempotent; set
`CREATE_BACKUP=0` only for a repeated test when a current backup already exists.

The pinned model is `granite4:3b`, 3.4B parameters, Q4_K_M, digest:

```text
89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f
```

## Operation

Start from the normal local assistant:

- `Okay Hal, active le mode interprète français vers anglais`.
- `Okay Hal, active le mode interprète anglais vers français`.

After the confirmation, continuous listening stays visibly active and each
utterance is translated and spoken locally. The session ends after ten minutes,
when privacy mode is enabled, or when continuous listening is stopped. The
speaker's triple click toggles continuous listening and therefore exits the
interpreter. `script.muse_swap_interpreter_direction` provides the explicit
dashboard button for changing direction during a session.

Exit always restores the previously selected house pipeline and calls the
firmware action `esphome.muse_luxe_clear_conversation_context`. The agent keeps
at most one previous exchange while the session is active; the ESPHome
conversation identifier is explicitly cleared on exit, so a later house query
cannot resume the interpreter context. The reset counter is exposed as
`sensor.raspiaudio_muse_luxe_voice_context_resets`.

## Safety and limitations

- Translation agents receive no `assist` LLM API and no entities or tools.
- User text is treated as text to translate, including command-like phrases.
- Granite can mistranslate or omit nuance. Do not use this alpha for medical,
  legal, emergency or safety-critical interpretation.
- Only French and English are qualified. Add each new language as a separate,
  tested direction with a local Piper voice.
- There is no transcript archive in this package. Home Assistant may retain an
  unreachable in-memory chat session until its normal expiry, but the satellite
  cannot reuse it after context reset.
- Direction changes during the translation pipeline use the dashboard script;
  spoken house commands are intentionally translated rather than executed.

## Validation and rollback

```bash
scripts/check_interpreter_safety.py
python3 scripts/test_interpreter_safety.py
```

The live test validates model digest, agents, pipelines, translations, voice
start, direction swap, physical-exit behavior, synthetic timeout, context-reset
counter and exact pipeline restoration. A short English Piper hardware test is
also part of qualification.

For rollback, first remove `/config/packages/muse_interpreter.yaml` and
`/config/custom_sentences/fr/muse_interpreter.yaml`, restart HA, and remove the
two interpreter pipelines/subentries in the UI. Only then restore the previous
firmware; otherwise the HA package would call an API action absent from the old
image. The named `pre-muse-interpreter-*` HA backup is the final recovery path.

## References

- [Home Assistant local voice setup](https://www.home-assistant.io/voice_control/voice_remote_local_assistant/)
- [Assist pipeline architecture](https://developers.home-assistant.io/docs/voice/pipelines/)
- [Ollama integration and tool controls](https://www.home-assistant.io/integrations/ollama)
- [Local Piper TTS actions](https://www.home-assistant.io/voice_control/using_tts_in_automation/)

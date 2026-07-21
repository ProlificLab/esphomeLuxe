#!/usr/bin/env python3
"""Exercise the local interpreter agents, pipelines and bounded session."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request


BASE_URL = "http://127.0.0.1:8123"
SELECTS = (
    "select.raspiaudio_muse_luxe_assistant",
    "select.raspiaudio_muse_luxe_assistant_2",
)
FR_TO_EN = "Interprete - Francais vers anglais"
EN_TO_FR = "Interprete - Anglais vers francais"


def request(path: str, token: str, data: dict | None = None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        if response.status == 204:
            return None
        return json.load(response)


def access_token() -> str:
    with open("/config/.storage/auth", encoding="utf-8") as auth_file:
        auth = json.load(auth_file)
    refresh_token = next(
        item
        for item in auth["data"]["refresh_tokens"]
        if item["token_type"] == "normal"
    )
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token["token"],
            "client_id": refresh_token["client_id"],
        }
    ).encode()
    with urllib.request.urlopen(
        urllib.request.Request(BASE_URL + "/auth/token", data=body), timeout=30
    ) as response:
        return json.load(response)["access_token"]


def state(token: str, entity_id: str) -> dict:
    return request(f"/api/states/{entity_id}", token)


def service(token: str, domain: str, name: str, data: dict | None = None):
    return request(f"/api/services/{domain}/{name}", token, data or {})


def wait_state(token: str, entity_id: str, expected: str, timeout: int = 20) -> None:
    deadline = time.monotonic() + timeout
    while state(token, entity_id)["state"] != expected:
        if time.monotonic() >= deadline:
            current = state(token, entity_id)["state"]
            raise RuntimeError(f"{entity_id} did not become {expected}; current={current}")
        time.sleep(0.25)


def wait_numeric_above(
    token: str, entity_id: str, previous: float, timeout: int = 20
) -> float:
    deadline = time.monotonic() + timeout
    while True:
        current_state = state(token, entity_id)["state"]
        try:
            current = float(current_state)
        except (TypeError, ValueError):
            current = previous
        if current > previous:
            return current
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"{entity_id} did not increase above {previous}; current={current_state}"
            )
        time.sleep(0.25)


def conversation(token: str, agent_id: str, language: str, text: str) -> tuple[str, float]:
    started = time.monotonic()
    result = request(
        "/api/conversation/process",
        token,
        {"text": text, "language": language, "agent_id": agent_id},
    )
    elapsed = time.monotonic() - started
    speech = result["response"]["speech"]["plain"]["speech"]
    return speech, elapsed


def local_intent(token: str, text: str) -> str:
    result = request(
        "/api/conversation/process",
        token,
        {"text": text, "language": "fr", "agent_id": "conversation.home_assistant"},
    )
    return result["response"]["speech"]["plain"]["speech"]


def verify_configuration() -> None:
    with urllib.request.urlopen("http://10.10.30.20:11435/api/tags", timeout=30) as response:
        models = json.load(response).get("models", [])
    model = next((item for item in models if item.get("name") == "granite4:3b"), None)
    if not model or model.get("digest") != (
        "89962fcc75239ac434cdebceb6b7e0669397f92eaef9c487774b718bc36a3e5f"
    ):
        raise RuntimeError("The pinned Granite interpreter model is missing or changed")

    with open(
        "/config/.storage/core.config_entries", encoding="utf-8"
    ) as entries_file:
        entries = json.load(entries_file)["data"]["entries"]
    entry = next(
        item
        for item in entries
        if item["domain"] == "ollama"
        and item["data"].get("url") == "http://10.10.30.20:11435"
    )
    expected_titles = {"Muse Interprete FR vers EN", "Muse Interprete EN vers FR"}
    agents = {
        item["title"]: item
        for item in entry.get("subentries", [])
        if item["title"] in expected_titles
    }
    if set(agents) != expected_titles:
        raise RuntimeError(f"Missing interpreter agents: {expected_titles - set(agents)}")
    for title, agent in agents.items():
        data = agent["data"]
        if data.get("model") != "granite4:3b":
            raise RuntimeError(f"Unexpected interpreter model for {title}")
        if int(data.get("max_history", -1)) != 1 or data.get("llm_hass_api"):
            raise RuntimeError(f"Interpreter agent has history or tools: {title}")
        if int(data.get("num_ctx", 0)) != 2048 or data.get("think") is not False:
            raise RuntimeError(f"Interpreter agent is not resource bounded: {title}")

    with open(
        "/config/.storage/assist_pipeline.pipelines", encoding="utf-8"
    ) as pipelines_file:
        pipelines = json.load(pipelines_file)["data"]["items"]
    expected = {
        FR_TO_EN: ("fr", "en_US", "en_US-lessac-medium"),
        EN_TO_FR: ("en", "fr_FR", "fr_FR-siwis-medium"),
    }
    for name, (stt_language, tts_language, voice) in expected.items():
        pipeline = next((item for item in pipelines if item["name"] == name), None)
        if not pipeline:
            raise RuntimeError(f"Missing interpreter pipeline: {name}")
        if (
            pipeline.get("stt_engine") != "stt.faster_whisper"
            or pipeline.get("stt_language") != stt_language
            or pipeline.get("tts_engine") != "tts.piper"
            or pipeline.get("tts_language") != tts_language
            or pipeline.get("tts_voice") != voice
            or pipeline.get("prefer_local_intents") is not False
        ):
            raise RuntimeError(f"Unsafe or incomplete interpreter pipeline: {pipeline}")


def main() -> None:
    verify_configuration()
    token = access_token()
    required = {
        "input_boolean.muse_interpreter_active",
        "input_select.muse_interpreter_direction",
        "input_text.muse_interpreter_previous_pipeline",
        "timer.muse_interpreter_session",
        "sensor.muse_interpreter_status",
        "script.muse_start_interpreter",
        "script.muse_swap_interpreter_direction",
        "script.muse_stop_interpreter",
    }
    entity_ids = {item["entity_id"] for item in request("/api/states", token)}
    if missing := required - entity_ids:
        raise RuntimeError(f"Missing interpreter entities: {sorted(missing)}")
    services = request("/api/services", token)
    esphome_services = next(
        item["services"] for item in services if item["domain"] == "esphome"
    )
    if "muse_luxe_clear_conversation_context" not in esphome_services:
        raise RuntimeError("The firmware context-reset action is unavailable")
    if state(token, "switch.raspiaudio_muse_luxe_privacy_mode")["state"] != "off":
        raise RuntimeError("Refusing to test while physical privacy mode is active")
    if state(token, "input_boolean.muse_interpreter_active")["state"] != "off":
        raise RuntimeError("Refusing to interrupt an active interpreter session")

    translations = []
    for agent, language, text, required_words in (
        (
            "conversation.muse_interprete_fr_vers_en",
            "fr",
            "Ferme la fenêtre avant que la pluie ne commence.",
            ("close", "window", "rain"),
        ),
        (
            "conversation.muse_interprete_en_vers_fr",
            "en",
            "Could you tell me where the nearest pharmacy is?",
            ("pharmacie", "proche"),
        ),
    ):
        speech, elapsed = conversation(token, agent, language, text)
        if not all(word in speech.casefold() for word in required_words):
            raise RuntimeError(f"Translation quality smoke test failed: {speech}")
        translations.append({"agent": agent, "seconds": round(elapsed, 3)})

    original = {entity_id: state(token, entity_id)["state"] for entity_id in SELECTS}
    reset_before = float(
        state(token, "sensor.raspiaudio_muse_luxe_voice_context_resets")["state"]
    )
    try:
        service(
            token,
            "script",
            "muse_start_interpreter",
            {"direction": "fr_to_en", "announce": False},
        )
        wait_state(token, "input_boolean.muse_interpreter_active", "on")
        wait_state(token, SELECTS[0], FR_TO_EN)
        wait_state(token, SELECTS[1], FR_TO_EN)
        wait_state(token, "switch.raspiaudio_muse_luxe_continuous_conversation", "on")
        wait_state(token, "timer.muse_interpreter_session", "active")
        if state(token, "input_text.muse_interpreter_previous_pipeline")["state"] != original[SELECTS[0]]:
            raise RuntimeError("Previous pipeline was not persisted")

        service(
            token,
            "script",
            "muse_swap_interpreter_direction",
            {"announce": False},
        )
        wait_state(token, "input_select.muse_interpreter_direction", "en_to_fr")
        wait_state(token, SELECTS[0], EN_TO_FR)
        wait_state(token, SELECTS[1], EN_TO_FR)

        service(
            token,
            "switch",
            "turn_off",
            {"entity_id": "switch.raspiaudio_muse_luxe_continuous_conversation"},
        )
        wait_state(token, "input_boolean.muse_interpreter_active", "off")
        wait_state(token, SELECTS[0], original[SELECTS[0]])
        wait_state(token, SELECTS[1], original[SELECTS[1]])
        wait_state(token, "timer.muse_interpreter_session", "idle")
        wait_state(token, "input_select.muse_interpreter_direction", "inactive")
        reset_after_physical_exit = wait_numeric_above(
            token,
            "sensor.raspiaudio_muse_luxe_voice_context_resets",
            reset_before,
        )

        local_intent(token, "active le mode interprète français vers anglais")
        wait_state(token, "input_boolean.muse_interpreter_active", "on")
        wait_state(token, "input_select.muse_interpreter_direction", "fr_to_en")
        request(
            "/api/events/timer.finished",
            token,
            {"entity_id": "timer.muse_interpreter_session"},
        )
        wait_state(token, "input_boolean.muse_interpreter_active", "off")
        wait_state(token, SELECTS[0], original[SELECTS[0]])
        wait_state(token, SELECTS[1], original[SELECTS[1]])
    finally:
        service(
            token,
            "input_boolean",
            "turn_off",
            {"entity_id": "input_boolean.muse_interpreter_active"},
        )
        service(
            token,
            "switch",
            "turn_off",
            {"entity_id": "switch.raspiaudio_muse_luxe_continuous_conversation"},
        )
        for entity_id, option in original.items():
            service(
                token,
                "select",
                "select_option",
                {"entity_id": entity_id, "option": option},
            )

    print(
        json.dumps(
            {
                "status": "pass",
                "translations": translations,
                "session": "start_swap_physical_exit_voice_start_timeout_restore",
                "history_previous_rounds": 1,
                "context_reset_counter": reset_after_physical_exit,
                "tools": False,
                "maximum_seconds": 600,
            }
        )
    )


if __name__ == "__main__":
    main()

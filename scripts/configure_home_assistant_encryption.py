import json
import sys
import urllib.parse
import urllib.request


ENTRY_ID = sys.argv[1]
ENCRYPTION_KEY = sys.argv[2]
BASE_URL = "http://127.0.0.1:8123"


def request(path, token, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


with open("/config/.storage/auth", encoding="utf-8") as auth_file:
    auth = json.load(auth_file)
refresh_token = next(
    item
    for item in auth["data"]["refresh_tokens"]
    if item["token_type"] == "normal"
)
token_body = urllib.parse.urlencode(
    {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token["token"],
        "client_id": refresh_token["client_id"],
    }
).encode()
with urllib.request.urlopen(
    urllib.request.Request(BASE_URL + "/auth/token", data=token_body), timeout=30
) as response:
    access_token = json.load(response)["access_token"]

with open("/config/.storage/core.config_entries", encoding="utf-8") as entries_file:
    entries = json.load(entries_file)["data"]["entries"]
entry = next(item for item in entries if item["entry_id"] == ENTRY_ID)

flow = request(
    "/api/config/config_entries/flow",
    access_token,
    {"handler": "esphome", "entry_id": ENTRY_ID},
)
if flow.get("type") != "form" or flow.get("step_id") != "user":
    raise RuntimeError(f"Unexpected reconfigure flow: {flow}")

flow = request(
    f"/api/config/config_entries/flow/{flow['flow_id']}",
    access_token,
    {"host": entry["data"]["host"], "port": entry["data"]["port"]},
)
if flow.get("type") != "form" or flow.get("step_id") != "encryption_key":
    raise RuntimeError(f"Unexpected encryption step: {flow}")

result = request(
    f"/api/config/config_entries/flow/{flow['flow_id']}",
    access_token,
    {"noise_psk": ENCRYPTION_KEY},
)
if result.get("type") not in ("create_entry", "abort"):
    raise RuntimeError(f"Encryption migration failed: {result}")

print(json.dumps({"type": result.get("type"), "reason": result.get("reason")}))

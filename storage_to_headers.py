# storage_to_headers.py
import json, pathlib, sys

SECRETS_PATH = pathlib.Path(".secrets/storage_state.json")
OUT_DIR = pathlib.Path("playwright")
OUT_DIR.mkdir(parents=True, exist_ok=True)

RED_PATH = OUT_DIR / "booking_api_headers.json"             # redacted (safe)
RUNTIME_PATH = OUT_DIR / ".booking_api_headers.runtime.json" # real headers (gitignore!)

API_ORIGIN = "https://cyon-syd-v4-api-d1-03.azurewebsites.net"  # base host; test_fetch overrides path/query

def main():
    if not SECRETS_PATH.exists():
        sys.exit(f"Missing {SECRETS_PATH}. Run your login script first.")

    state = json.loads(SECRETS_PATH.read_text())
    origins = state.get("origins", [])
    rb = next((o for o in origins if o.get("origin") == "https://resourcebooker.rmit.edu.au"), None)
    if not rb:
        sys.exit("Could not find origin https://resourcebooker.rmit.edu.au in storage_state.json")

    ls = rb.get("localStorage", [])
    auth_item = next((x for x in ls if x.get("name") == "scientia-session-authorization"), None)
    if not auth_item:
        sys.exit("Could not find localStorage key 'scientia-session-authorization'")

    try:
        auth_json = json.loads(auth_item["value"])
        access_token = auth_json["access_token"]
    except Exception as e:
        sys.exit(f"Failed to parse access_token: {e}")

    # Minimal headers needed server-side
    real_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    # Redacted copy for the non-sensitive file
    redacted_headers = {
        "Authorization": "Bearer <REDACTED>",
        "Accept": "application/json",
    }

    # Save files. We store "url" with just the host; test_fetch.py replaces path/query via CLI.
    redacted = {"url": API_ORIGIN, "headers": redacted_headers}
    runtime  = {"url": API_ORIGIN, "headers": real_headers}

    RED_PATH.write_text(json.dumps(redacted, indent=2))
    RUNTIME_PATH.write_text(json.dumps(runtime, indent=2))

    print(f"Wrote redacted → {RED_PATH}")
    print(f"Wrote runtime  → {RUNTIME_PATH}  (add to .gitignore)")

if __name__ == "__main__":
    main()

"""Monster-AI page plus the live party list.

Roblox servers send a heartbeat with header X-Api-Key.
The page reads GET /api/parties and never sees the key.
A party disappears 30 seconds after its last heartbeat.
"""

import json
import os
import re
import time
from hmac import compare_digest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEY_FILE = ROOT / ".api-key"
TTL_SECONDS = 30
PARTIES = {}
ID_RE = re.compile(r"^[A-Z0-9]{2,8}$")
UNIVERSES = {"fnaf", "tadc", "flip"}
FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/styles.css": "styles.css",
    "/god.js": "god.js",
}
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


def load_key():
    env = os.environ.get("NOTHING_API_KEY", "").strip()
    if env:
        return env
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    return ""


API_KEY = load_key()


def public_row(party):
    minutes = max(0, int((time.time() - party["born"]) // 60))
    return {
        "id": party["id"],
        "form": party["form"],
        "world": party["world"],
        "players": party["players"],
        "minutes": minutes,
        "note": party["note"],
    }


def live_rows():
    now = time.time()
    dead = [party_id for party_id, party in PARTIES.items() if now - party["seen"] > TTL_SECONDS]
    for party_id in dead:
        del PARTIES[party_id]
    rows = [public_row(party) for party in PARTIES.values()]
    rows.sort(key=lambda row: row["id"])
    return rows


def clean_party(data):
    if not isinstance(data, dict):
        return None, "body must be an object"
    party_id = str(data.get("id", "")).strip().upper()
    form = str(data.get("form") or data.get("universe") or "fnaf").strip().lower()
    if not ID_RE.match(party_id):
        return None, "id must be 2-8 letters or numbers"
    if form not in UNIVERSES:
        return None, "universe must be fnaf, tadc, or flip"
    try:
        world = int(data.get("world", 1))
        players = int(data.get("players", 0))
    except (TypeError, ValueError):
        return None, "world and players must be numbers"
    world = min(20, max(1, world))
    players = min(100, max(0, players))
    note = str(data.get("note") or "").replace("\n", " ").strip()[:180]
    if not note:
        note = "The server is running. You are already inside it."
    return {
        "id": party_id,
        "form": form,
        "world": world,
        "players": players,
        "note": note,
    }, None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

    def send_json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        if not API_KEY:
            return False
        got = self.headers.get("X-Api-Key", "")
        return compare_digest(got, API_KEY)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Api-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self.send_json(200, {"ok": True})
            return
        if path == "/api/parties":
            self.send_json(200, live_rows())
            return
        name = FILES.get(path)
        if not name:
            self.send_json(404, {"error": "not found"})
            return
        file_path = ROOT / name
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TYPES[file_path.suffix])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/parties":
            self.send_json(404, {"error": "not found"})
            return
        if not self.authorized():
            self.send_json(401, {"error": "bad key"})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 2 or length > 4000:
            self.send_json(400, {"error": "bad body"})
            return
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            self.send_json(400, {"error": "bad json"})
            return
        party, error = clean_party(data)
        if error:
            self.send_json(400, {"error": error})
            return
        now = time.time()
        previous = PARTIES.get(party["id"])
        party["born"] = previous["born"] if previous else now
        party["seen"] = now
        PARTIES[party["id"]] = party
        self.send_json(200, public_row(party))


def main():
    if not API_KEY:
        raise SystemExit("Set NOTHING_API_KEY or create Nothing/.api-key")
    port = int(os.environ.get("PORT", "4173"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("Nothing monster AI page http://127.0.0.1:%s/" % port)
    server.serve_forever()


if __name__ == "__main__":
    main()

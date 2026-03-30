import os
import json
import hashlib
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler
import gspread
from google.oauth2.service_account import Credentials

META_PIXEL_ID   = "393920814533839"
META_CAPI_TOKEN = os.environ.get("META_CAPI_TOKEN", "")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def _normalize_phone(wa: str) -> str:
    digits = "".join(c for c in wa if c.isdigit())
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    return digits


def _send_capi_prospect(event_id: str, email: str, wa: str, nama: str, client_ip: str, user_agent: str):
    if not META_CAPI_TOKEN:
        return
    user_data = {
        "em": [_sha256(email)],
        "ph": [_sha256(_normalize_phone(wa))],
    }
    if nama:
        parts = nama.strip().lower().split()
        user_data["fn"] = [_sha256(parts[0])]
        if len(parts) > 1:
            user_data["ln"] = [_sha256(parts[-1])]
    if client_ip:
        user_data["client_ip_address"] = client_ip
    if user_agent:
        user_data["client_user_agent"] = user_agent

    payload = json.dumps({
        "data": [{
            "event_name": "Prospect",
            "event_time": int(datetime.now().timestamp()),
            "event_id": event_id,
            "action_source": "website",
            "user_data": user_data,
        }]
    }).encode()

    url = f"https://graph.facebook.com/v20.0/{META_PIXEL_ID}/events?access_token={META_CAPI_TOKEN}"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # Don't fail the request if CAPI call fails

_GS_CREDS_RAW = os.environ.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS", "")
GOOGLE_SHEETS_ID = os.environ.get("GOOGLE_SHEETS_ID", "")


def _append_lead(row: list):
    creds_info = json.loads(_GS_CREDS_RAW)
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(GOOGLE_SHEETS_ID).sheet1
    ws.append_row(row, value_input_option="USER_ENTERED")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)

            nama         = data.get("nama", "").strip()
            email        = data.get("email", "").strip()
            wa           = data.get("wa", "").strip()
            profesi      = data.get("profesi", "").strip()
            utm_ops      = data.get("utm_ops", "").strip()
            utm_source   = data.get("utm_source", "").strip()
            utm_campaign = data.get("utm_campaign", "").strip()
            utm_medium   = data.get("utm_medium", "").strip()
            utm_content  = data.get("utm_content", "").strip()
            event_id     = data.get("event_id", "").strip()

            if not nama or not email:
                self._json({"error": "Nama dan email wajib diisi"}, 400)
                return

            # Fire Meta CAPI Prospect event (server-side, deduplicated via event_id)
            if event_id and email:
                client_ip  = self.headers.get("x-forwarded-for", self.client_address[0])
                user_agent = self.headers.get("user-agent", "")
                _send_capi_prospect(event_id, email, wa, nama, client_ip, user_agent)

            if _GS_CREDS_RAW and GOOGLE_SHEETS_ID:
                try:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    _append_lead([timestamp, nama, email, wa, profesi, utm_ops, utm_source, utm_campaign, utm_medium, utm_content])
                except Exception as e:
                    self._json({"success": True, "sheet_error": str(e)}, 200)
                    return

            self._json({"success": True}, 200)

        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _json(self, obj, status):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

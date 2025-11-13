# backend/utils/sms.py
import os
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional

# SMSPortal credentials (set these in Render / local .env)
SMSP_CLIENT_ID = os.getenv("SMSP_CLIENT_ID")        # e.g. the "Client ID" from SMSPortal (username)
SMSP_API_SECRET = os.getenv("SMSP_API_SECRET")      # e.g. the "API Secret" from SMSPortal (password)
SMSP_API_URL = os.getenv("SMSP_API_URL", "https://rest.smsportal.com/bulkmessages")
# Optional fallback/test number (use full international format e.g. +27838555008)
SMSP_DEFAULT_TO = os.getenv("SMSP_DEFAULT_TO")

def _normalize_sa_number(num: str) -> str:
    """Simple normalization: if number starts with 0 (e.g. 083...), convert to +27... .
    If the number already starts with + or 00, return as-is. If it is missing country code
    and doesn't start with 0, leave it as-is (ask user to provide international format)."""
    if not num:
        return num
    s = num.strip()
    if s.startswith("+"):
        return s
    if s.startswith("00"):
        return "+" + s[2:]
    if s.startswith("0"):
        # ASSUMPTION: numbers starting with 0 are South African local numbers → convert to +27
        return "+27" + s[1:]
    return s

def send_sms(message: str, to_number: Optional[str] = None) -> dict:
    """
    Send SMS using SMSPortal bulk endpoint.
    - Expects SMSP_CLIENT_ID and SMSP_API_SECRET in env.
    - to_number should be international format (e.g. +2783...), or local SA (083...) which will be converted.
    - Returns parsed JSON response from SMSPortal, raises Exception on failure.
    """
    if not SMSP_CLIENT_ID or not SMSP_API_SECRET:
        raise Exception("SMSPortal credentials not configured. Set SMSP_CLIENT_ID and SMSP_API_SECRET.")

    if not to_number:
        if not SMSP_DEFAULT_TO:
            raise Exception("Destination number not provided and SMSP_DEFAULT_TO not configured.")
        to_number = SMSP_DEFAULT_TO

    # Normalize (helpful if user supplies 083... local SA number)
    to_number = _normalize_sa_number(to_number)

    payload = {
        "messages": [
            {
                "content": message,
                "destination": to_number
            }
        ]
    }

    try:
        resp = requests.post(
            SMSP_API_URL,
            json=payload,
            auth=HTTPBasicAuth(SMSP_CLIENT_ID, SMSP_API_SECRET),
            timeout=15,
        )
    except Exception as e:
        raise Exception(f"Network error sending SMS: {e}")

    if resp.status_code < 200 or resp.status_code >= 300:
        # include response body for easier debugging
        raise Exception(f"SMSPortal error: {resp.status_code} - {resp.text}")

    # respond with parsed JSON (SMSPortal returns metadata about messages)
    try:
        return resp.json()
    except Exception:
        return {"raw_response": resp.text}

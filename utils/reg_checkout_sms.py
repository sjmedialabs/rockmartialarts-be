"""SMS for registration checkout (OTP, welcome, renewal).

Env:
  SMS_PROVIDER=json | msg91 | form | smslogin   (default: json)
  SMS_API_URL, SMS_API_KEY, SMS_SENDER_ID, SMS_USERNAME (for smslogin)
  DLT_TEMPLATE_* → template_id / templateid where applicable

- json: POST JSON to SMS_API_URL (shape configurable via SMS_JSON_*).
- msg91: POST form to MSG91 sendhttp (SMS_API_KEY=authkey; SMS_API_URL optional override).
- form: POST application/x-www-form-urlencoded to SMS_API_URL (field names via SMS_FORM_*).
- smslogin: GET https://smslogin.co/v3/api.php (docs) with username, apikey, senderid, mobile,
  message, templateid — set SMS_USERNAME, SMS_API_KEY, SMS_SENDER_ID; optional SMS_API_URL override.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)

MSG91_DEFAULT_URL = "https://api.msg91.com/api/sendhttp.php"
SMSLOGIN_DEFAULT_URL = "https://smslogin.co/v3/api.php"


def _smslogin_username() -> str:
    return (os.getenv("SMS_USERNAME") or "").strip()


def sms_provider_expects_delivery() -> bool:
    """True when env says we use a real SMS gateway (not local JSON stub)."""
    prov = (os.getenv("SMS_PROVIDER") or "json").strip().lower()
    if prov in ("smslogin", "smslogin_co", "rockacademy", "msg91"):
        return True
    if prov in ("form", "urlencoded", "x-www-form-urlencoded"):
        return bool((os.getenv("SMS_API_URL") or "").strip())
    if prov == "json":
        return bool((os.getenv("SMS_API_URL") or "").strip())
    return False


def is_sms_delivery_configured() -> bool:
    """True when real delivery is expected (OTP should fail if send fails)."""
    prov = (os.getenv("SMS_PROVIDER") or "json").strip().lower()
    if prov == "msg91":
        return bool(
            (os.getenv("SMS_API_KEY") or "").strip()
            and (os.getenv("SMS_SENDER_ID") or "").strip()
        )
    return bool((os.getenv("SMS_API_URL") or "").strip())


def _digits_only(phone: str) -> str:
    return "".join(c for c in (phone or "") if c.isdigit())


def format_sms_mobile(phone: str) -> str:
    """
    E.164-style for India: 91 + last 10 digits when appropriate.
    MSG91/country=91 expects 9198xxxxxxxx without '+'.
    """
    d = _digits_only(phone)
    if len(d) >= 10:
        core = d[-10:]
        if len(d) == 10 or (len(d) == 12 and d.startswith("91")):
            return "91" + core
        if d.startswith("91") and len(d) >= 12:
            return d[:12] if len(d) == 12 else "91" + d[-10:]
        return "91" + core
    return d or phone.strip()


def _send_msg91(phone: str, message: str, template_id: Optional[str]) -> bool:
    authkey = (os.getenv("SMS_API_KEY") or "").strip()
    sender = (os.getenv("SMS_SENDER_ID") or "").strip()
    if not authkey or not sender:
        logger.error("MSG91 requires SMS_API_KEY and SMS_SENDER_ID")
        return False

    url = (os.getenv("SMS_API_URL") or "").strip() or MSG91_DEFAULT_URL
    mobiles = format_sms_mobile(phone)
    params: Dict[str, Any] = {
        "authkey": authkey,
        "mobiles": mobiles,
        "message": message,
        "sender": sender,
        "route": (os.getenv("SMS_MSG91_ROUTE") or "4").strip(),
        "country": "91",
        "response": "json",
    }
    if template_id:
        params["DLT_TE_ID"] = template_id

    try:
        r = requests.post(url, data=params, timeout=20)
        text = (r.text or "")[:500]
        if r.status_code >= 400:
            logger.error("MSG91 HTTP %s: %s", r.status_code, text)
            return False
        try:
            data = r.json()
            if isinstance(data, dict):
                t = str(data.get("type", "")).lower()
                if t == "success":
                    logger.info("MSG91 sent ok: %s", str(data)[:200])
                    return True
                if data.get("message") and t == "error":
                    logger.error("MSG91 error: %s", data)
                    return False
        except ValueError:
            pass
        low = text.lower()
        if "invalid" in low and "success" not in low:
            logger.error("MSG91 response: %s", text)
            return False
        logger.info("MSG91 response: %s", text[:200])
        return True
    except requests.RequestException as e:
        logger.exception("MSG91 request failed: %s", e)
        return False


def _send_smslogin(phone: str, message: str, template_id: Optional[str]) -> bool:
    """Rock Academy / smslogin.co v3 API — GET with query parameters."""
    base = (os.getenv("SMS_API_URL") or "").strip() or SMSLOGIN_DEFAULT_URL
    username = _smslogin_username()
    apikey = (os.getenv("SMS_API_KEY") or "").strip()
    sender = (os.getenv("SMS_SENDER_ID") or "").strip()
    if not username or not apikey or not sender:
        logger.error("smslogin requires SMS_USERNAME, SMS_API_KEY, SMS_SENDER_ID")
        return False

    params: Dict[str, Any] = {
        "username": username,
        "apikey": apikey,
        "senderid": sender,
        "mobile": format_sms_mobile(phone),
        "message": message,
    }
    if template_id:
        params["templateid"] = template_id

    try:
        r = requests.get(base, params=params, timeout=25)
        text = (r.text or "").strip()
        snippet = text[:800]
        if r.status_code >= 400:
            logger.error("smslogin HTTP %s: %s", r.status_code, snippet)
            return False
        low = snippet.lower()
        err_markers = (
            "invalid",
            "authentication",
            "auth fail",
            "insufficient",
            "balance",
            "error",
            "failed",
            "reject",
            "unauthor",
        )
        # Short API status lines; avoid flagging normal English in long echoes
        if len(text) < 500 and any(m in low for m in err_markers):
            # Some gateways return "success" alongside other words — prefer positive signals
            if "success" in low or "submitted" in low or "accepted" in low:
                logger.info("smslogin ok: %s", snippet)
                return True
            logger.error("smslogin error response: %s", snippet)
            return False
        logger.info("smslogin response: %s", snippet)
        return True
    except requests.RequestException as e:
        logger.exception("smslogin request failed: %s", e)
        return False


def _send_form(phone: str, message: str, template_id: Optional[str]) -> bool:
    url = (os.getenv("SMS_API_URL") or "").strip()
    if not url:
        return True

    api_key = (os.getenv("SMS_API_KEY") or "").strip()
    sender = (os.getenv("SMS_SENDER_ID") or "").strip()

    mobile_field = (os.getenv("SMS_FORM_MOBILE_FIELD") or "mobile").strip()
    message_field = (os.getenv("SMS_FORM_MESSAGE_FIELD") or "message").strip()
    sender_field = (os.getenv("SMS_FORM_SENDER_FIELD") or "sender_id").strip()
    template_field = (os.getenv("SMS_FORM_TEMPLATE_FIELD") or "template_id").strip()
    key_field = (os.getenv("SMS_FORM_API_KEY_FIELD") or "apikey").strip()

    data: Dict[str, Any] = {
        mobile_field: format_sms_mobile(phone),
        message_field: message,
    }
    if sender:
        data[sender_field] = sender
    if template_id:
        data[template_field] = template_id
    if api_key:
        data[key_field] = api_key

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    extra_header = (os.getenv("SMS_FORM_AUTH_HEADER") or "").strip()
    if extra_header and api_key:
        parts = extra_header.split(":", 1)
        if len(parts) == 2:
            headers[parts[0].strip()] = parts[1].strip().replace("{key}", api_key)
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    try:
        r = requests.post(url, data=data, headers=headers, timeout=20)
        if r.status_code >= 400:
            logger.error("SMS form API error %s: %s", r.status_code, r.text[:500])
            return False
        return True
    except requests.RequestException as e:
        logger.exception("SMS form request failed: %s", e)
        return False


def _send_json(phone: str, message: str, template_id: Optional[str]) -> bool:
    url = (os.getenv("SMS_API_URL") or "").strip()
    api_key = (os.getenv("SMS_API_KEY") or "").strip()
    sender = (os.getenv("SMS_SENDER_ID") or "").strip()

    if not url:
        logger.info(
            "[reg-checkout SMS stub] to=%s template=%s msg=%s",
            phone,
            template_id,
            message[:120],
        )
        return True

    phone_key = (os.getenv("SMS_JSON_PHONE_FIELD") or "to").strip()
    message_key = (os.getenv("SMS_JSON_MESSAGE_FIELD") or "message").strip()
    sender_key = (os.getenv("SMS_JSON_SENDER_FIELD") or "sender_id").strip()
    template_key = (os.getenv("SMS_JSON_TEMPLATE_FIELD") or "template_id").strip()

    payload: Dict[str, Any] = {
        phone_key: format_sms_mobile(phone),
        message_key: message,
    }
    if sender:
        payload[sender_key] = sender
    if template_id:
        payload[template_key] = template_id

    merge = (os.getenv("SMS_JSON_EXTRA") or "").strip()
    if merge:
        try:
            extra = json.loads(merge)
            if isinstance(extra, dict):
                payload.update(extra)
        except Exception:
            logger.warning("SMS_JSON_EXTRA is not valid JSON; ignored")

    auth_style = (os.getenv("SMS_AUTH_STYLE") or "bearer").strip().lower()
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        if auth_style == "bearer":
            headers["Authorization"] = f"Bearer {api_key}"
        elif auth_style == "authkey":
            headers["authkey"] = api_key
        elif auth_style == "x-api-key":
            headers["X-Api-Key"] = api_key
        elif auth_style == "api-key":
            headers["api-key"] = api_key

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        if r.status_code >= 400:
            logger.error("SMS API error %s: %s", r.status_code, r.text[:500])
            return False
        return True
    except requests.RequestException as e:
        logger.exception("SMS request failed: %s", e)
        return False


def send_registration_sms(
    phone: str,
    message: str,
    template_id: Optional[str] = None,
) -> bool:
    prov = (os.getenv("SMS_PROVIDER") or "json").strip().lower()
    if prov == "msg91":
        return _send_msg91(phone, message, template_id)
    if prov in ("smslogin", "smslogin_co", "rockacademy"):
        return _send_smslogin(phone, message, template_id)
    if prov in ("form", "urlencoded", "x-www-form-urlencoded"):
        return _send_form(phone, message, template_id)
    return _send_json(phone, message, template_id)

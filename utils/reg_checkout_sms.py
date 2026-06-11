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

Proxy: Outbound requests use a Session with trust_env=False so HTTP_PROXY / HTTPS_PROXY /
ALL_PROXY pointing at a dead local proxy (e.g. 127.0.0.1) do not break the SMS gateway call.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional, Tuple
import requests

# (success, optional short reason for API clients — never include secrets)
SmsSendResult = Tuple[bool, Optional[str]]


def _sms_fail_reason(msg: str) -> str:
    s = (msg or "").strip().replace("\n", " ")
    if len(s) > 240:
        return s[:237] + "..."
    return s


def public_sms_failure_hint(reason: Optional[str]) -> Optional[str]:
    """Avoid echoing query strings or keys to the browser."""
    if not reason:
        return None
    low = reason.lower()
    if any(x in low for x in ("apikey", "api_key", "password=", "username=")):
        return "SMS gateway returned an error (see server logs for details)."
    return _sms_fail_reason(reason)

logger = logging.getLogger(__name__)

MSG91_DEFAULT_URL = "https://api.msg91.com/api/sendhttp.php"
SMSLOGIN_DEFAULT_URL = "https://smslogin.co/v3/api.php"

# Outbound SMS must bypass HTTP(S)_PROXY from the environment. Passing
# proxies={"http": None, "https": None} is not enough in some stacks — urllib3
# still applies env proxy (e.g. HTTPS_PROXY=http://127.0.0.1:7890), causing
# ProxyError / connection to 127.0.0.1. Session.trust_env=False fixes that.
def _sms_http_session() -> requests.Session:
    sess = requests.Session()
    sess.trust_env = False
    return sess


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


def _send_msg91(phone: str, message: str, template_id: Optional[str]) -> SmsSendResult:
    authkey = (os.getenv("SMS_API_KEY") or "").strip()
    sender = (os.getenv("SMS_SENDER_ID") or "").strip()
    if not authkey or not sender:
        logger.error("MSG91 requires SMS_API_KEY and SMS_SENDER_ID")
        return False, "MSG91 requires SMS_API_KEY and SMS_SENDER_ID"

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
        with _sms_http_session() as s:
            r = s.post(url, data=params, timeout=20)
        text = (r.text or "")[:500]
        if r.status_code >= 400:
            logger.error("MSG91 HTTP %s: %s", r.status_code, text)
            return False, f"MSG91 HTTP {r.status_code}"
        try:
            data = r.json()
            if isinstance(data, dict):
                t = str(data.get("type", "")).lower()
                if t == "success":
                    logger.info("MSG91 sent ok: %s", str(data)[:200])
                    return True, None
                if data.get("message") and t == "error":
                    logger.error("MSG91 error: %s", data)
                    return False, str(data.get("message") or "MSG91 error")[:200]
        except ValueError:
            pass
        low = text.lower()
        if "invalid" in low and "success" not in low:
            logger.error("MSG91 response: %s", text)
            return False, text[:200]
        logger.info("MSG91 response: %s", text[:200])
        return True, None
    except requests.RequestException as e:
        logger.exception("MSG91 request failed: %s", e)
        return False, str(e)[:200]


def _send_smslogin(phone: str, message: str, template_id: Optional[str]) -> SmsSendResult:
    """Rock Academy / smslogin.co v3 API — GET with query parameters."""
    base = (os.getenv("SMS_API_URL") or "").strip() or SMSLOGIN_DEFAULT_URL
    # If .env pasted a full example URL with ?username=…, strip the query; params are set below.
    if "?" in base:
        base = base.split("?", 1)[0].strip() or SMSLOGIN_DEFAULT_URL
    username = _smslogin_username()
    apikey = (os.getenv("SMS_API_KEY") or "").strip()
    sender = (os.getenv("SMS_SENDER_ID") or "").strip()
    if not username or not apikey or not sender:
        logger.error("smslogin requires SMS_USERNAME, SMS_API_KEY, SMS_SENDER_ID")
        return False, "Missing SMS_USERNAME, SMS_API_KEY, or SMS_SENDER_ID"

    tid_s = (template_id or "").strip()
    allow_no_tid = os.getenv("SMSLOGIN_ALLOW_NO_TEMPLATE", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not tid_s and not allow_no_tid:
        logger.error(
            "smslogin: missing DLT template id — Indian DLT OTP usually requires templateid; SMS may not deliver"
        )
        return (
            False,
            "Set DLT_OTP_VARIABLE_ID to your DLT template id from smslogin (not the message text). "
            "Override only if your account allows it: SMSLOGIN_ALLOW_NO_TEMPLATE=true.",
        )

    params: Dict[str, Any] = {
        "username": username,
        "apikey": apikey,
        "senderid": sender,
        "mobile": format_sms_mobile(phone),
        "message": message,
    }
    if tid_s:
        params["templateid"] = tid_s

    try:
        with _sms_http_session() as s:
            r = s.get(base, params=params, timeout=25)
        text = (r.text or "").strip()
        snippet = text[:800]
        if r.status_code >= 400:
            logger.error("smslogin HTTP %s: %s", r.status_code, snippet)
            return False, f"HTTP {r.status_code} from SMS gateway"

        # JSON body (many gateways)
        try:
            data = r.json()
            if isinstance(data, dict):
                st = str(
                    data.get("status")
                    or data.get("Status")
                    or data.get("response")
                    or data.get("code")
                    or ""
                ).lower()
                if st in ("success", "ok", "1", "true", "200", "sent"):
                    logger.info("smslogin ok (json): %s", str(data)[:300])
                    return True, None
                if data.get("message_id") or data.get("msgid") or data.get("MsgID"):
                    logger.info("smslogin ok (id): %s", str(data)[:300])
                    return True, None
                err = (
                    data.get("error")
                    or data.get("message")
                    or data.get("msg")
                    or data.get("description")
                )
                if err:
                    logger.error("smslogin json error: %s", data)
                    return False, str(err)[:200]
        except ValueError:
            pass

        low = snippet.lower()
        ok_markers = (
            "success",
            "submitted",
            "accepted",
            "sent",
            "message_id",
            "msgid",
            "request successfully",
            "sms sent",
            "delivered",
        )
        if any(m in low for m in ok_markers):
            logger.info("smslogin ok: %s", snippet)
            return True, None

        err_markers = (
            "authentication",
            "auth fail",
            "insufficient",
            "invalid user",
            "invalid api",
            "invalid mobile",
            "invalid sender",
            "recharge",
            "low balance",
            "failed",
            "reject",
            "unauthor",
            "dlt",
            "template",
        )
        if len(text) < 800 and any(m in low for m in err_markers):
            logger.error("smslogin error response: %s", snippet)
            return False, snippet[:220]

        # Long or ambiguous 200 response — treat as success (log for support)
        if r.status_code == 200:
            logger.info("smslogin response (assumed ok): %s", snippet)
            return True, None
        return False, snippet[:220] or "Unknown SMS gateway response"
    except requests.RequestException as e:
        logger.exception("smslogin request failed: %s", e)
        return False, str(e)[:200]


def _send_form(phone: str, message: str, template_id: Optional[str]) -> SmsSendResult:
    url = (os.getenv("SMS_API_URL") or "").strip()
    if not url:
        return True, None

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
        with _sms_http_session() as s:
            r = s.post(url, data=data, headers=headers, timeout=20)
        if r.status_code >= 400:
            logger.error("SMS form API error %s: %s", r.status_code, r.text[:500])
            return False, f"HTTP {r.status_code}"
        return True, None
    except requests.RequestException as e:
        logger.exception("SMS form request failed: %s", e)
        return False, str(e)[:200]


def _send_json(phone: str, message: str, template_id: Optional[str]) -> SmsSendResult:
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
        return True, None

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
        with _sms_http_session() as s:
            r = s.post(url, json=payload, headers=headers, timeout=20)
        if r.status_code >= 400:
            logger.error("SMS API error %s: %s", r.status_code, r.text[:500])
            return False, f"HTTP {r.status_code}"
        return True, None
    except requests.RequestException as e:
        logger.exception("SMS request failed: %s", e)
        return False, str(e)[:200]


def send_registration_sms(
    phone: str,
    message: str,
    template_id: Optional[str] = None,
) -> SmsSendResult:
    prov = (os.getenv("SMS_PROVIDER") or "json").strip().lower()
    if prov == "msg91":
        return _send_msg91(phone, message, template_id)
    if prov in ("smslogin", "smslogin_co", "rockacademy"):
        return _send_smslogin(phone, message, template_id)
    if prov in ("form", "urlencoded", "x-www-form-urlencoded"):
        return _send_form(phone, message, template_id)
    return _send_json(phone, message, template_id)

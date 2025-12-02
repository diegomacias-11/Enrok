import logging
import time
from typing import Iterable, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_token_cache = {"access_token": None, "expires_at": 0.0}


class GraphEmailError(Exception):
    pass


def _get_access_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] - 30 > now:
        return _token_cache["access_token"]

    tenant_id = settings.GRAPH_TENANT_ID
    client_id = settings.GRAPH_CLIENT_ID
    client_secret = settings.GRAPH_CLIENT_SECRET
    if not tenant_id or not client_id or not client_secret:
        raise GraphEmailError("Faltan credenciales de Graph (client_id/client_secret/tenant_id).")

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    try:
        resp = requests.post(token_url, data=data, timeout=15)
    except Exception as exc:  # pragma: no cover
        raise GraphEmailError(f"Error de red al obtener token: {exc}") from exc

    if resp.status_code != 200:
        raise GraphEmailError(f"Token Graph fallo: {resp.status_code} {resp.text}")

    payload = resp.json()
    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in", 0)
    if not access_token:
        raise GraphEmailError("La respuesta de token no incluyo access_token.")

    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = now + int(expires_in)
    return access_token


def send_graph_mail(
    to: str,
    subject: str,
    html_body: Optional[str] = None,
    text_body: Optional[str] = None,
    cc: Optional[Iterable[str]] = None,
    bcc: Optional[Iterable[str]] = None,
    save_to_sent: bool = False,
) -> None:
    from_email = settings.EMAIL_FROM
    if not from_email:
        raise GraphEmailError("EMAIL_FROM no esta configurado.")

    access_token = _get_access_token()
    url = f"https://graph.microsoft.com/v1.0/users/{from_email}/sendMail"

    def _recipients(addresses):
        return [{"emailAddress": {"address": addr}} for addr in addresses] if addresses else []

    # Prefer HTML; fallback to texto plano si no hay HTML
    if html_body:
        body = {"contentType": "HTML", "content": html_body}
    elif text_body:
        body = {"contentType": "Text", "content": text_body}
    else:
        raise GraphEmailError("No se proporciono cuerpo del mensaje.")

    message = {
        "subject": subject,
        "body": body,
        "toRecipients": _recipients([to]),
    }

    cc_list = list(cc) if cc else []
    bcc_list = list(bcc) if bcc else []
    if cc_list:
        message["ccRecipients"] = _recipients(cc_list)
    if bcc_list:
        message["bccRecipients"] = _recipients(bcc_list)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "message": message,
        "saveToSentItems": save_to_sent,
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    if resp.status_code not in (202, 200):
        logger.error("Graph sendMail fallo: %s %s", resp.status_code, resp.text)
        raise GraphEmailError(f"Graph sendMail fallo: {resp.status_code} {resp.text}")

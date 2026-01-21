import logging
import os
import unicodedata

from django.conf import settings
from django.utils import timezone

from google.oauth2 import service_account
from google.auth import default as google_auth_default
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

MONTHS_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def _normalize_header(value: str) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("\u200b", "")
    text = "".join(ch for ch in text if ch.isalnum() or ch in "| ")
    text = " ".join(text.strip().lower().split())
    return text


def _column_letter(index: int) -> str:
    index += 1
    letters = []
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def _get_sheets_service():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if creds_json:
        creds = service_account.Credentials.from_service_account_info(
            _safe_json_loads(creds_json), scopes=SHEETS_SCOPES
        )
        return build("sheets", "v4", credentials=creds)

    creds, _ = google_auth_default(scopes=SHEETS_SCOPES)
    return build("sheets", "v4", credentials=creds)


def _safe_json_loads(value: str) -> dict:
    import json

    return json.loads(value)


def _sheet_title_for_date(fecha):
    month_name = MONTHS_ES.get(fecha.month)
    if not month_name:
        return None
    return f"{month_name} {fecha.year}"


def append_dispersion_row(dispersion):
    sheet_id = settings.GOOGLE_SHEETS_CONFEDIN if dispersion.cliente.ac == "CONFEDIN" else settings.GOOGLE_SHEETS_OTHERS
    if not sheet_id:
        return "Google Sheets ID no configurado."

    sheet_title = _sheet_title_for_date(dispersion.fecha)
    if not sheet_title:
        return "No se pudo resolver la hoja por fecha."

    try:
        service = _get_sheets_service()
        header_resp = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{sheet_title}'!1:1",
        ).execute()
        headers = header_resp.get("values", [])
        if not headers:
            return f"Hoja '{sheet_title}' sin encabezados."

        header_row = headers[0]
        normalized = {_normalize_header(value): idx for idx, value in enumerate(header_row)}

        if "fecha" in normalized:
            required = {
                "fecha": "fecha",
                "hr de peticion": "hr de peticion",
                "cliente": "cliente",
                "estructura": "estructura",
                "cuenta": "cuenta",
                "monto": "monto",
            }
        else:
            required = {
                "|": "|",
                "hr de peticion": "hr de peticion",
                "cliente": "cliente",
                "estructura": "estructura",
                "cuenta": "cuenta",
                "monto": "monto",
            }

        missing = [key for key in required.values() if key not in normalized]
        if missing:
            return f"Encabezados faltantes en {sheet_title}: {', '.join(missing)}"

        date_key = "fecha" if "fecha" in normalized else "|"
        date_col = _column_letter(normalized[date_key])
        col_values = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{sheet_title}'!{date_col}:{date_col}",
        ).execute().get("values", [])

        target_row = 2
        for idx, row in enumerate(col_values[1:], start=2):
            if not row or not str(row[0]).strip():
                target_row = idx
                break
        else:
            target_row = len(col_values) + 1

        now = timezone.localtime()
        fecha_value = dispersion.fecha.strftime("%d/%m/%Y")
        hora_value = now.strftime("%H:%M")
        try:
            estructura = dispersion.cliente.get_ac_display()
        except Exception:
            estructura = dispersion.cliente.ac or ""

        values = {
            "fecha": fecha_value,
            "|": fecha_value,
            "hr de peticion": hora_value,
            "cliente": dispersion.cliente.razon_social or "",
            "estructura": estructura,
            "cuenta": "",
            "monto": str(dispersion.monto_dispersion or ""),
        }

        data = []
        for _, header_key in required.items():
            col_letter = _column_letter(normalized[header_key])
            value = values[header_key]
            data.append(
                {
                    "range": f"'{sheet_title}'!{col_letter}{target_row}",
                    "values": [[value]],
                }
            )

        service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data},
        ).execute()
    except Exception as exc:
        logger.warning("Error al enviar a Sheets: %s", exc)
        return str(exc)

    return None

from __future__ import annotations

import base64
import imaplib
import re
from dataclasses import dataclass
from datetime import datetime
from email import message_from_bytes
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Iterable, Optional

import requests


@dataclass(frozen=True)
class EmailMessage:
    message_id: str
    subject: str
    body_text: str
    internal_date: datetime


def _strip_html(html: str) -> str:
    if not html:
        return ""
    # Простой stripping без внешних зависимостей.
    return re.sub(r"<[^>]+>", " ", html)


def _get_text_from_email_message(msg: Message) -> str:
    if msg.is_multipart():
        plain_text = None
        html_text = None
        for part in msg.walk():
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                decoded = payload.decode(charset, errors="ignore")
            except Exception:
                decoded = payload.decode("utf-8", errors="ignore")

            if content_type == "text/plain" and plain_text is None:
                plain_text = decoded
            elif content_type == "text/html" and html_text is None:
                html_text = decoded
        if plain_text:
            return plain_text
        if html_text:
            return _strip_html(html_text)
        return ""
    # non-multipart
    payload = msg.get_payload(decode=True)
    if payload is None:
        return msg.get_payload() or ""
    charset = msg.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="ignore")
    except Exception:
        return payload.decode("utf-8", errors="ignore")


class GmailProvider:
    provider = "gmail"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        # Lazy imports: чтобы не падать при импорте модуля без зависимостей.
        from google.auth.transport.requests import Request  # noqa: F401

        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    @staticmethod
    def scope() -> str:
        return "https://www.googleapis.com/auth/gmail.readonly"

    def build_authorization_url(self, state: str, code_verifier: Optional[str] = None) -> str:
        from google_auth_oauthlib.flow import Flow

        client_config = {
            "web": {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        flow = Flow.from_client_config(
            client_config=client_config,
            scopes=[self.scope()],
            state=state,
            redirect_uri=self._redirect_uri,
            code_verifier=code_verifier,
            # Если передали code_verifier, то PKCE уже будет корректно верифицирован.
            # Если не передали — библиотека может не сгенерировать его, поэтому предпочитаем
            # всегда передавать code_verifier со стороны backend.
        )
        # access_type=offline -> refresh_token
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def exchange_code_for_refresh_token(self, code: str, code_verifier: Optional[str] = None) -> str:
        from google_auth_oauthlib.flow import Flow

        client_config = {
            "web": {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        flow = Flow.from_client_config(
            client_config=client_config,
            scopes=[self.scope()],
            redirect_uri=self._redirect_uri,
            code_verifier=code_verifier,
        )
        flow.fetch_token(code=code)
        tokens = flow.credentials
        if not getattr(tokens, "refresh_token", None):
            raise RuntimeError("Gmail: refresh_token not returned")
        return tokens.refresh_token

    def list_messages(
        self,
        refresh_token: str,
        last_synced_at: Optional[datetime],
        limit: int,
    ) -> Iterable[EmailMessage]:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=[self.scope()],
        )
        creds.refresh(Request())

        service = build("gmail", "v1", credentials=creds)

        q = ""
        if last_synced_at:
            after_date = (last_synced_at.date()).strftime("%Y/%m/%d")
            # "after:" использует дату (UTC) без времени; для надежности обычно уходит 1 день.
            q = f"after:{after_date}"

        res = (
            service.users()
            .messages()
            .list(userId="me", q=q, maxResults=limit)
            .execute()
        )
        messages = res.get("messages", []) or []

        def decode_body_b64url(data: str) -> str:
            if not data:
                return ""
            raw = base64.urlsafe_b64decode(data.encode("utf-8"))
            return raw.decode("utf-8", errors="ignore")

        def extract_from_payload(payload: dict) -> str:
            mime = payload.get("mimeType")
            body = payload.get("body") or {}
            data = body.get("data")
            if mime == "text/plain" and data:
                return decode_body_b64url(data)
            # рекурсивно по part'ам
            for part in payload.get("parts") or []:
                val = extract_from_payload(part)
                if val:
                    return val
            # fallback на text/html
            for part in payload.get("parts") or []:
                if part.get("mimeType") == "text/html":
                    pdata = (part.get("body") or {}).get("data")
                    if pdata:
                        return _strip_html(decode_body_b64url(pdata))
            return ""

        for m in messages:
            message_id = m.get("id")
            if not message_id:
                continue
            full = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            payload = full.get("payload") or {}
            headers = payload.get("headers") or []
            subject = ""
            for h in headers:
                if (h.get("name") or "").lower() == "subject":
                    subject = h.get("value") or ""
                    break
            internal_ms = full.get("internalDate")
            try:
                internal_date = datetime.utcfromtimestamp(int(internal_ms) / 1000.0)
            except Exception:
                internal_date = datetime.utcnow()
            body_text = extract_from_payload(payload)
            yield EmailMessage(
                message_id=str(message_id),
                subject=subject,
                body_text=body_text,
                internal_date=internal_date,
            )


class MailRuProvider:
    provider = "mailru"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    @staticmethod
    def scope() -> str:
        # Для чтения IMAP через OAuth2 обычно достаточно mail.imap.
        return "mail.imap userinfo"

    def build_authorization_url(self, state: str) -> str:
        base = "https://o2.mail.ru/login"
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": self.scope(),
            "state": state,
        }
        # Формируем URL вручную, чтобы не зависеть от urllib.
        parts = [f"{k}={requests.utils.quote(str(v), safe='')}" for k, v in params.items()]
        return f"{base}?{'&'.join(parts)}"

    def exchange_code_for_refresh_token(self, code: str, code_verifier: Optional[str] = None) -> str:
        _ = code_verifier  # Mail.ru не использует PKCE в этом коде
        url = "https://o2.mail.ru/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect_uri,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        r = requests.post(url, data=data, timeout=30)
        r.raise_for_status()
        payload = r.json()
        refresh_token = payload.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("Mail.ru: refresh_token not returned")
        return refresh_token

    def refresh_access_token(self, refresh_token: str) -> str:
        url = "https://appsmail.ru/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refresh_token,
        }
        r = requests.post(url, data=data, timeout=30)
        r.raise_for_status()
        payload = r.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise RuntimeError("Mail.ru: access_token not returned")
        return access_token

    def list_messages(
        self,
        user_email: str,
        refresh_token: str,
        last_synced_at: Optional[datetime],
        limit: int,
    ) -> Iterable[EmailMessage]:
        access_token = self.refresh_access_token(refresh_token)

        imap = imaplib.IMAP4_SSL("imap.mail.ru", 993)

        auth_string = f"user={user_email}\x01auth=Bearer {access_token}\x01\x01"

        def auth_func(_: bytes) -> bytes:
            return base64.b64encode(auth_string.encode("utf-8"))

        imap.authenticate("XOAUTH2", auth_func)
        imap.select("INBOX")

        # SINCE использует формат типа: 17-Sep-2025 (UTC не гарантируется, но достаточно для sync)
        if last_synced_at:
            since_str = last_synced_at.strftime("%d-%b-%Y")
            status, data = imap.search(None, "SINCE", since_str)
        else:
            status, data = imap.search(None, "ALL")

        if status != "OK":
            imap.logout()
            return []

        ids = (data[0] or b"").split()
        if not ids:
            imap.logout()
            return []

        # Берем последние limit писем.
        ids_to_fetch = ids[-limit:]

        out: list[EmailMessage] = []
        for msg_id in ids_to_fetch:
            msg_id_str = msg_id.decode("utf-8") if isinstance(msg_id, (bytes, bytearray)) else str(msg_id)
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data:
                continue
            raw_bytes = None
            for part in msg_data:
                if isinstance(part, tuple) and part[1]:
                    raw_bytes = part[1]
                    break
            if not raw_bytes:
                continue
            msg = message_from_bytes(raw_bytes)
            subject = msg.get("Subject") or ""
            # Date header (если не удается — fallback)
            internal_date = datetime.utcnow()
            try:
                dt = parsedate_to_datetime(msg.get("Date") or "")
                if dt:
                    internal_date = dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt
            except Exception:
                pass
            body_text = _get_text_from_email_message(msg)
            out.append(
                EmailMessage(
                    message_id=msg_id_str,
                    subject=subject,
                    body_text=body_text,
                    internal_date=internal_date,
                )
            )

        imap.logout()
        return out


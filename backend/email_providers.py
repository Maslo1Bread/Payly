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
        )
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
            for part in payload.get("parts") or []:
                val = extract_from_payload(part)
                if val:
                    return val
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

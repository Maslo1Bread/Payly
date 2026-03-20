from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .fernet_utils import decrypt_json, encrypt_json, get_fernet


@dataclass(frozen=True)
class ProviderTokenRecord:
    refresh_token: str
    last_synced_at: Optional[datetime] = None


class ProviderTokenStore:
    """
    Хранилище refresh_token (в зашифрованном файле) и last_synced_at.

    Это упрощение под текущий учебный проект: не добавляем таблицы в БД.
    """

    def __init__(self, key_path: Path, data_path: Path):
        self._key_path = key_path
        self._data_path = data_path
        self._fernet = get_fernet(self._key_path)
        self._cache: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._data_path.exists():
            self._cache = {}
            return
        try:
            raw = self._data_path.read_bytes()
            if not raw:
                self._cache = {}
                return
            self._cache = decrypt_json(raw, self._key_path)
        except Exception:
            self._cache = {}

    def _save(self) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._cache
        encrypted = encrypt_json(payload, self._key_path)
        self._data_path.write_bytes(encrypted)

    def _key(self, user_id: int, provider: str) -> str:
        return f"{user_id}:{provider}"

    def get(self, user_id: int, provider: str) -> Optional[ProviderTokenRecord]:
        record = self._cache.get(self._key(user_id, provider))
        if not record:
            return None
        refresh_token = record.get("refresh_token")
        if not refresh_token:
            return None
        last_synced_at_raw = record.get("last_synced_at")
        last_synced_at = None
        if isinstance(last_synced_at_raw, str) and last_synced_at_raw:
            try:
                last_synced_at = datetime.fromisoformat(last_synced_at_raw)
            except Exception:
                last_synced_at = None
        return ProviderTokenRecord(refresh_token=refresh_token, last_synced_at=last_synced_at)

    def set_refresh_token(self, user_id: int, provider: str, refresh_token: str) -> None:
        k = self._key(user_id, provider)
        record = self._cache.get(k, {})
        record["refresh_token"] = refresh_token
        self._cache[k] = record
        self._save()

    def set_last_synced_at(self, user_id: int, provider: str, last_synced_at: datetime) -> None:
        k = self._key(user_id, provider)
        record = self._cache.get(k, {})
        record["last_synced_at"] = last_synced_at.isoformat()
        self._cache[k] = record
        self._save()


class OAuthStateStore:
    """
    Хранилище OAuth state (CSRF) в зашифрованном файле.
    """

    def __init__(self, key_path: Path, data_path: Path):
        self._key_path = key_path
        self._data_path = data_path
        self._cache: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._data_path.exists():
            self._cache = {}
            return
        try:
            raw = self._data_path.read_bytes()
            if not raw:
                self._cache = {}
                return
            self._cache = decrypt_json(raw, self._key_path)
        except Exception:
            self._cache = {}

    def _save(self) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        encrypted = encrypt_json(self._cache, self._key_path)
        self._data_path.write_bytes(encrypted)

    def put(self, state: str, user_id: int, provider: str, code_verifier: Optional[str] = None) -> None:
        payload: dict[str, Any] = {"user_id": user_id, "provider": provider}
        if code_verifier:
            payload["code_verifier"] = code_verifier
        self._cache[state] = payload
        self._save()

    def pop(self, state: str) -> Optional[dict[str, Any]]:
        record = self._cache.pop(state, None)
        self._save()
        return record


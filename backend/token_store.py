import json
from pathlib import Path
from typing import Dict

from cryptography.fernet import Fernet, InvalidToken


class EncryptedTokenStore:

    def __init__(self, key_path: Path, data_path: Path):
        self._key_path = key_path
        self._data_path = data_path
        self._fernet = Fernet(self._get_or_create_key())
        self._cache: Dict[str, int] = {}
        self._cache = self._load()

    def _get_or_create_key(self) -> bytes:
        self._key_path.parent.mkdir(parents=True, exist_ok=True)
        if self._key_path.exists():
            return self._key_path.read_bytes()
        key = Fernet.generate_key()
        self._key_path.write_bytes(key)
        return key

    def _load(self) -> Dict[str, int]:
        if not self._data_path.exists():
            return {}
        raw = self._data_path.read_bytes()
        if not raw:
            return {}
        try:
            decrypted = self._fernet.decrypt(raw)
        except InvalidToken:
            return {}
        try:
            data = json.loads(decrypted.decode("utf-8"))
        except Exception:
            return {}

        if not isinstance(data, dict):
            return {}

        out: Dict[str, int] = {}
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, int):
                out[k] = v
        return out

    def _save(self) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._cache, ensure_ascii=False).encode("utf-8")
        encrypted = self._fernet.encrypt(payload)
        self._data_path.write_bytes(encrypted)

    def get_user_id(self, token: str) -> int | None:
        return self._cache.get(token)

    def set_token(self, token: str, user_id: int) -> None:
        self._cache[token] = user_id
        self._save()

    def revoke(self, token: str) -> None:
        if token in self._cache:
            self._cache.pop(token, None)
            self._save()


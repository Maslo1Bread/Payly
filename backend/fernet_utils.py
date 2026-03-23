from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet


def _get_or_create_key(key_path: Path) -> bytes:
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    return key


def get_fernet(key_path: Path) -> Fernet:
    return Fernet(_get_or_create_key(key_path))


def encrypt_json(payload: Any, key_path: Path) -> bytes:
    """
    Шифрует JSON-данные целиком (удобно для простых file-based хранилищ).
    """
    fernet = get_fernet(key_path)
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return fernet.encrypt(raw)


def decrypt_json(ciphertext: bytes, key_path: Path) -> Any:
    fernet = get_fernet(key_path)
    raw = fernet.decrypt(ciphertext)
    return json.loads(raw.decode("utf-8"))


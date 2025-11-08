"""Shopot document serialization helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .crypto import (
    EncryptedPayload,
    LegacyEncryptedPayload,
    decrypt,
    decrypt_legacy,
    decrypt_v2,
    encrypt,
)


@dataclass
class ShopotDocument:
    text: str

    def encrypt(self, key_material: str) -> EncryptedPayload:
        return encrypt(self.text.encode("utf-8"), key_material)

    @classmethod
    def decrypt(cls, payload: EncryptedPayload, key_material: str) -> "ShopotDocument":
        plaintext = decrypt(payload, key_material)
        return cls(text=plaintext.decode("utf-8"))

    def save(self, path: str | Path, key_material: str) -> None:
        payload = self.encrypt(key_material)
        data = {
            "version": 3,
            "payload": payload.to_dict(),
        }
        Path(path).write_text(json.dumps(data))

    @classmethod
    def load(cls, path: str | Path, key_material: str) -> "ShopotDocument":
        data = json.loads(Path(path).read_text())
        version = data.get("version", 1)
        payload_data = data["payload"]

        if version == 1:
            payload = LegacyEncryptedPayload.from_dict(payload_data)
            plaintext = decrypt_legacy(payload, key_material)
            return cls(text=plaintext.decode("utf-8"))
        if version == 2:
            payload = EncryptedPayload.from_dict(payload_data)
            plaintext = decrypt_v2(payload, key_material)
            return cls(text=plaintext.decode("utf-8"))
        if version == 3:
            payload = EncryptedPayload.from_dict(payload_data)
            return cls.decrypt(payload, key_material)

        raise ValueError(f"Unsupported Shopot document version: {version}")

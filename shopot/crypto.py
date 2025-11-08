"""Simple symmetric encryption helpers for Shopot documents."""
from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass


@dataclass
class EncryptedPayload:
    salt: bytes
    ciphertext: bytes

    def to_dict(self) -> dict[str, str]:
        return {
            "salt": base64.b64encode(self.salt).decode("ascii"),
            "ciphertext": base64.b64encode(self.ciphertext).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "EncryptedPayload":
        return cls(
            salt=base64.b64decode(data["salt"]),
            ciphertext=base64.b64decode(data["ciphertext"]),
        )


def _keystream(seed: bytes, length: int) -> bytes:
    counter = 0
    stream = bytearray()
    while len(stream) < length:
        counter_bytes = counter.to_bytes(8, "big")
        digest = hashlib.sha512(seed + counter_bytes).digest()
        stream.extend(digest)
        counter += 1
    return bytes(stream[:length])


def encrypt(plaintext: bytes, key_material: str) -> EncryptedPayload:
    salt = os.urandom(16)
    seed = hashlib.sha256(key_material.encode("utf-8") + salt).digest()
    keystream = _keystream(seed, len(plaintext))
    ciphertext = bytes(p ^ k for p, k in zip(plaintext, keystream))
    return EncryptedPayload(salt=salt, ciphertext=ciphertext)


def decrypt(payload: EncryptedPayload, key_material: str) -> bytes:
    seed = hashlib.sha256(key_material.encode("utf-8") + payload.salt).digest()
    keystream = _keystream(seed, len(payload.ciphertext))
    plaintext = bytes(c ^ k for c, k in zip(payload.ciphertext, keystream))
    return plaintext

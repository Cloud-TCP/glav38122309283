"""Encryption helpers for Shopot documents."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass


PBKDF2_ITERATIONS = 200_000
SALT_SIZE = 16
NONCE_SIZE = 16


@dataclass
class EncryptedPayload:
    """Payload format for the modern encryption schemes (versions 2 and 3)."""

    salt: bytes
    nonce: bytes
    ciphertext: bytes
    mac: bytes

    def to_dict(self) -> dict[str, str]:
        return {
            "salt": base64.b64encode(self.salt).decode("ascii"),
            "nonce": base64.b64encode(self.nonce).decode("ascii"),
            "ciphertext": base64.b64encode(self.ciphertext).decode("ascii"),
            "mac": base64.b64encode(self.mac).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "EncryptedPayload":
        return cls(
            salt=base64.b64decode(data["salt"]),
            nonce=base64.b64decode(data["nonce"]),
            ciphertext=base64.b64decode(data["ciphertext"]),
            mac=base64.b64decode(data["mac"]),
        )


@dataclass
class LegacyEncryptedPayload:
    """Payload produced by the original prototype cipher (version 1)."""

    salt: bytes
    ciphertext: bytes

    def to_dict(self) -> dict[str, str]:
        return {
            "salt": base64.b64encode(self.salt).decode("ascii"),
            "ciphertext": base64.b64encode(self.ciphertext).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "LegacyEncryptedPayload":
        return cls(
            salt=base64.b64decode(data["salt"]),
            ciphertext=base64.b64decode(data["ciphertext"]),
        )


def _derive_keys(key_material: str, salt: bytes) -> tuple[bytes, bytes]:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        key_material.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=64,
    )
    return derived[:32], derived[32:]


def _material_bytes(key_material: str) -> bytes:
    material = key_material.encode("utf-8")
    if not material:
        raise ValueError("Key material must not be empty")
    return material


def _keystream_v2(key: bytes, nonce: bytes, length: int) -> bytes:
    counter = 0
    stream = bytearray()
    while len(stream) < length:
        counter_bytes = counter.to_bytes(8, "big")
        digest = hmac.new(key, nonce + counter_bytes, hashlib.sha512).digest()
        stream.extend(digest)
        counter += 1
    return bytes(stream[:length])


def _keystream_v3(
    key: bytes,
    salt: bytes,
    nonce: bytes,
    material: bytes,
    length: int,
) -> bytes:
    material_len = len(material)
    if material_len == 0:
        raise ValueError("Key material must not be empty")

    stream = bytearray()
    counter = 0
    while len(stream) < length:
        counter_bytes = counter.to_bytes(8, "big")
        rotation = counter % material_len
        rotated = material[rotation:] + material[:rotation]
        digest_input = salt + nonce + counter_bytes + rotated
        digest = hmac.new(key, digest_input, hashlib.sha512).digest()
        stream.extend(digest)
        counter += 1
    return bytes(stream[:length])


def encrypt_v2(plaintext: bytes, key_material: str) -> EncryptedPayload:
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    enc_key, mac_key = _derive_keys(key_material, salt)
    keystream = _keystream_v2(enc_key, nonce, len(plaintext))
    ciphertext = bytes(p ^ k for p, k in zip(plaintext, keystream))
    mac = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    return EncryptedPayload(salt=salt, nonce=nonce, ciphertext=ciphertext, mac=mac)


def decrypt_v2(payload: EncryptedPayload, key_material: str) -> bytes:
    enc_key, mac_key = _derive_keys(key_material, payload.salt)
    expected_mac = hmac.new(
        mac_key, payload.nonce + payload.ciphertext, hashlib.sha256
    ).digest()
    if not hmac.compare_digest(expected_mac, payload.mac):
        raise ValueError("Encrypted payload authentication failed")
    keystream = _keystream_v2(enc_key, payload.nonce, len(payload.ciphertext))
    return bytes(c ^ k for c, k in zip(payload.ciphertext, keystream))


def encrypt(plaintext: bytes, key_material: str) -> EncryptedPayload:
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    material = _material_bytes(key_material)
    enc_key, mac_key = _derive_keys(key_material, salt)
    keystream = _keystream_v3(enc_key, salt, nonce, material, len(plaintext))
    ciphertext = bytes(p ^ k for p, k in zip(plaintext, keystream))
    material_digest = hashlib.sha512(material).digest()
    mac = hmac.new(
        mac_key, salt + nonce + ciphertext + material_digest, hashlib.sha256
    ).digest()
    return EncryptedPayload(salt=salt, nonce=nonce, ciphertext=ciphertext, mac=mac)


def decrypt(payload: EncryptedPayload, key_material: str) -> bytes:
    material = _material_bytes(key_material)
    enc_key, mac_key = _derive_keys(key_material, payload.salt)
    material_digest = hashlib.sha512(material).digest()
    expected_mac = hmac.new(
        mac_key,
        payload.salt + payload.nonce + payload.ciphertext + material_digest,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(expected_mac, payload.mac):
        raise ValueError("Encrypted payload authentication failed")
    keystream = _keystream_v3(
        enc_key, payload.salt, payload.nonce, material, len(payload.ciphertext)
    )
    return bytes(c ^ k for c, k in zip(payload.ciphertext, keystream))


def encrypt_legacy(plaintext: bytes, key_material: str) -> LegacyEncryptedPayload:
    salt = os.urandom(16)
    seed = hashlib.sha256(key_material.encode("utf-8") + salt).digest()
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(plaintext):
        counter_bytes = counter.to_bytes(8, "big")
        digest = hashlib.sha512(seed + counter_bytes).digest()
        keystream.extend(digest)
        counter += 1
    ciphertext = bytes(p ^ k for p, k in zip(plaintext, keystream[: len(plaintext)]))
    return LegacyEncryptedPayload(salt=salt, ciphertext=ciphertext)


def decrypt_legacy(payload: LegacyEncryptedPayload, key_material: str) -> bytes:
    seed = hashlib.sha256(key_material.encode("utf-8") + payload.salt).digest()
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(payload.ciphertext):
        counter_bytes = counter.to_bytes(8, "big")
        digest = hashlib.sha512(seed + counter_bytes).digest()
        keystream.extend(digest)
        counter += 1
    return bytes(c ^ k for c, k in zip(payload.ciphertext, keystream[: len(payload.ciphertext)]))

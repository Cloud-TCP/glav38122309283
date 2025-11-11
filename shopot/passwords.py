"""Password to key derivation helpers."""
from __future__ import annotations

from typing import Iterable

from .keyfiles import KeyArray, LAYER_COUNT
from .patterns import PATTERN_COUNT, registry


def validate_password(password: str) -> None:
    if len(password) != LAYER_COUNT:
        raise ValueError(f"Password must be exactly {LAYER_COUNT} digits long")
    if not password.isdigit():
        raise ValueError("Password must contain digits only")
    for digit in password:
        if int(digit) >= PATTERN_COUNT:
            raise ValueError(f"Digit '{digit}' is not associated with a pattern")


def password_to_key_material(password: str, key_array: KeyArray) -> str:
    """Return the raw key material derived from password and key array."""

    validate_password(password)
    fragments: list[str] = []
    for layer_index, char in enumerate(password):
        pattern_index = int(char)
        layer = key_array.layer(layer_index)
        selected_elements = _collect_elements(pattern_index, layer)
        fragments.append("".join(selected_elements))
    return "".join(fragments)


def _collect_elements(pattern_index: int, layer) -> Iterable[str]:
    for row, col in registry.coordinates(pattern_index, layer):
        yield layer[row][col]

"""Utilities for loading and generating Shopot key array files (.shptk)."""
from __future__ import annotations

import json
import os
import random
import string
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

ArrayLayer = List[List[str]]
Array3D = List[ArrayLayer]

CHARACTERS = string.ascii_letters + string.digits
LAYER_COUNT = 10
GRID_SIZE = 77
ELEMENT_LENGTH = 2


@dataclass
class KeyArray:
    layers: Array3D

    @classmethod
    def generate(cls, *, seed: int | None = None) -> "KeyArray":
        rng = random.Random(seed)
        layers: Array3D = []
        for _ in range(LAYER_COUNT):
            layer: ArrayLayer = []
            for _ in range(GRID_SIZE):
                row = ["".join(rng.choice(CHARACTERS) for _ in range(ELEMENT_LENGTH)) for _ in range(GRID_SIZE)]
                layer.append(row)
            layers.append(layer)
        return cls(layers)

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "KeyArray":
        data = json.loads(Path(path).read_text())
        if not isinstance(data, list) or len(data) != LAYER_COUNT:
            raise ValueError("Invalid key file: unexpected structure")
        return cls(data)  # type: ignore[arg-type]

    def dump(self, path: str | os.PathLike[str]) -> None:
        ensure_directory(path)
        Path(path).write_text(json.dumps(self.layers))

    def layer(self, index: int) -> ArrayLayer:
        return self.layers[index]

    def as_text(self, index: int) -> str:
        layer = self.layer(index)
        return "\n".join(" ".join(row) for row in layer)


def ensure_directory(path: str | os.PathLike[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

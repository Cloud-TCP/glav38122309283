"""Pattern selection logic for Shopot key arrays."""
from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

Coordinate = Tuple[int, int]
Layer = Sequence[Sequence[str]]


class PatternRegistry:
    """Registry mapping digit strings to layer selection patterns.

    Each pattern returns a sequence of coordinates (row, column) that should be
    read from the supplied layer. The registry stores callables so that it is
    trivial to add new patterns in the future.
    """

    def __init__(self) -> None:
        self._patterns: List = []

    def register(self, func):
        self._patterns.append(func)
        return func

    def get(self, digit: int):
        try:
            return self._patterns[digit]
        except IndexError as exc:  # pragma: no cover - defensive programming
            raise ValueError(f"Unknown pattern index: {digit}") from exc

    def coordinates(self, digit: int, layer: Layer) -> Iterable[Coordinate]:
        pattern = self.get(digit)
        return pattern(layer)


registry = PatternRegistry()


def _all_coordinates(layer: Layer) -> Iterable[Coordinate]:
    size = len(layer)
    for row in range(size):
        for col in range(size):
            yield row, col


@registry.register
def pattern_fill(layer: Layer) -> Iterable[Coordinate]:
    """Return every coordinate in the layer (row-major order)."""

    return _all_coordinates(layer)


@registry.register
def pattern_checkerboard_a(layer: Layer) -> Iterable[Coordinate]:
    """Checkerboard pattern starting with (0, 0)."""

    size = len(layer)
    for row in range(size):
        for col in range(size):
            if (row + col) % 2 == 0:
                yield row, col


@registry.register
def pattern_checkerboard_b(layer: Layer) -> Iterable[Coordinate]:
    """Checkerboard pattern starting with (0, 1)."""

    size = len(layer)
    for row in range(size):
        for col in range(size):
            if (row + col) % 2 == 1:
                yield row, col


@registry.register
def pattern_plus(layer: Layer) -> Iterable[Coordinate]:
    """Return coordinates that form a plus sign."""

    size = len(layer)
    center = size // 2
    for col in range(size):
        yield center, col
    for row in range(size):
        if row != center:
            yield row, center


@registry.register
def pattern_border(layer: Layer) -> Iterable[Coordinate]:
    """Return only the border elements of the layer."""

    size = len(layer)
    last = size - 1
    for col in range(size):
        yield 0, col
    for row in range(1, last):
        yield row, 0
        yield row, last
    for col in range(size):
        yield last, col


@registry.register
def pattern_diagonal(layer: Layer) -> Iterable[Coordinate]:
    """Main diagonal from top-left to bottom-right."""

    size = len(layer)
    for i in range(size):
        yield i, i


@registry.register
def pattern_anti_diagonal(layer: Layer) -> Iterable[Coordinate]:
    """Secondary diagonal from top-right to bottom-left."""

    size = len(layer)
    for i in range(size):
        yield i, size - 1 - i


@registry.register
def pattern_spiral(layer: Layer) -> Iterable[Coordinate]:
    """Return coordinates in an outward-in spiral order."""

    size = len(layer)
    top, bottom, left, right = 0, size - 1, 0, size - 1
    while top <= bottom and left <= right:
        for col in range(left, right + 1):
            yield top, col
        top += 1
        for row in range(top, bottom + 1):
            yield row, right
        right -= 1
        if top <= bottom:
            for col in range(right, left - 1, -1):
                yield bottom, col
            bottom -= 1
        if left <= right:
            for row in range(bottom, top - 1, -1):
                yield row, left
            left += 1


@registry.register
def pattern_vertical_stripes(layer: Layer) -> Iterable[Coordinate]:
    """Take every other column, left to right."""

    size = len(layer)
    for col in range(0, size, 2):
        for row in range(size):
            yield row, col


@registry.register
def pattern_horizontal_stripes(layer: Layer) -> Iterable[Coordinate]:
    """Take every other row, top to bottom."""

    size = len(layer)
    for row in range(0, size, 2):
        for col in range(size):
            yield row, col


PATTERN_COUNT = len(registry._patterns)

"""Generate real image files in memory, so tests never depend on fixtures checked into git."""

from __future__ import annotations

import struct
import zlib


def png(width: int = 64, height: int = 64, rgb: tuple[int, int, int] = (16, 120, 72)) -> bytes:
    """A valid solid-colour RGB PNG."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    row = b"\x00" + bytes(rgb) * width
    raw = zlib.compress(row * height, 9)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


def file_payload(name: str, data: bytes, mime: str) -> dict[str, object]:
    return {"name": name, "mimeType": mime, "buffer": data}

from __future__ import annotations

import math
import os
import struct
import zlib
from pathlib import Path


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    length = struct.pack(">I", len(data))
    crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return length + tag + data + crc


def write_png(path: Path, width: int, height: int, pixels: bytes) -> None:
    """
    Запись простого PNG (RGB, 8-bit).
    pixels: bytes длиной width*height*3 (row-major).
    """
    if len(pixels) != width * height * 4:
        raise ValueError("pixels size mismatch")

    # Добавляем filter byte 0 перед каждой строкой
    raw = bytearray()
    row_len = width * 4
    for y in range(height):
        raw.append(0)
        start = y * row_len
        raw.extend(pixels[start : start + row_len])

    compressed = zlib.compress(bytes(raw), level=9)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit, RGBA
    data = (
        signature
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", compressed)
        + _png_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def render_icon(size: int) -> bytes:
    """
    Рисует простую иконку:
    белый фон, синяя цифра 9 с чёрной окантовкой.
    """
    S = float(size)
    cx = S * 0.5
    cy = S * 0.36
    R = S * 0.28
    hole_r = R * 0.55
    outline = max(1.0, S * 0.025)

    tail_w = S * 0.18
    tail_x0 = cx + R - tail_w * 0.8
    tail_x1 = tail_x0 + tail_w
    tail_y0 = cy + R * 0.1
    tail_y1 = S * 0.9

    # Внутренняя синяя форма (чуть меньше)
    Rb = R - outline
    tail_x0b = tail_x0 + outline
    tail_x1b = tail_x1 - outline
    tail_y0b = tail_y0 + outline
    tail_y1b = tail_y1 - outline

    white = (255, 255, 255, 255)
    blue = (30, 91, 255, 255)
    black = (0, 0, 0, 255)

    buf = bytearray(size * size * 4)

    def set_px(x: int, y: int, color: tuple[int, int, int, int]) -> None:
        idx = (y * size + x) * 4
        buf[idx : idx + 4] = bytes(color)

    for y in range(size):
        fy = y + 0.5
        for x in range(size):
            fx = x + 0.5

            # фон
            color = white

            # внешняя (чёрная) форма
            in_outer = (fx - cx) ** 2 + (fy - cy) ** 2 <= R * R
            in_tail = tail_x0 <= fx <= tail_x1 and tail_y0 <= fy <= tail_y1
            if in_outer or in_tail:
                color = black

            # внутренняя (синяя) форма
            in_inner = (fx - cx) ** 2 + (fy - cy) ** 2 <= Rb * Rb
            in_tail_b = tail_x0b <= fx <= tail_x1b and tail_y0b <= fy <= tail_y1b
            if in_inner or in_tail_b:
                color = blue

            # отверстие внутри "9"
            in_hole = (fx - cx) ** 2 + (fy - cy) ** 2 <= hole_r * hole_r
            if in_hole:
                color = white

            set_px(x, y, color)

    return bytes(buf)


def generate_iconset(out_dir: Path) -> None:
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    out_dir.mkdir(parents=True, exist_ok=True)

    for size, name in sizes:
        pixels = render_icon(size)
        write_png(out_dir / name, size, size, pixels)


def generate_png(path: Path, size: int = 1024) -> None:
    pixels = render_icon(size)
    write_png(path, size, size, pixels)


def generate_icns(iconset_dir: Path, out_path: Path) -> None:
    """
    Минимальный ICNS: контейнер с PNG-иконками разных размеров.
    """
    size_to_type = {
        16: b"icp4",
        32: b"icp5",
        64: b"icp6",
        128: b"ic07",
        256: b"ic08",
        512: b"ic09",
        1024: b"ic10",
    }

    chunks: list[bytes] = []
    total = 8
    for size, icns_type in size_to_type.items():
        # Берём PNG с нужным размером
        if size == 64:
            name = "icon_32x32@2x.png"
        elif size == 1024:
            name = "icon_512x512@2x.png"
        else:
            name = f"icon_{size}x{size}.png"
        png_path = iconset_dir / name
        data = png_path.read_bytes()
        length = 8 + len(data)
        chunk = icns_type + struct.pack(">I", length) + data
        chunks.append(chunk)
        total += length

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"icns" + struct.pack(">I", total) + b"".join(chunks))


def generate_ico(iconset_dir: Path, out_path: Path) -> None:
    """
    ICO контейнер с PNG-иконками.
    """
    sizes = [16, 32, 64, 128, 256]
    entries = []
    images = []

    offset = 6 + 16 * len(sizes)  # header + directory entries

    for size in sizes:
        if size == 64:
            name = "icon_32x32@2x.png"
        else:
            name = f"icon_{size}x{size}.png"
        png_path = iconset_dir / name
        data = png_path.read_bytes()
        images.append(data)
        width = size if size < 256 else 0
        height = size if size < 256 else 0
        entry = struct.pack(
            "<BBBBHHII",
            width,
            height,
            0,  # color count
            0,  # reserved
            1,  # planes
            32,  # bit count
            len(data),
            offset,
        )
        entries.append(entry)
        offset += len(data)

    header = struct.pack("<HHH", 0, 1, len(sizes))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(header + b"".join(entries) + b"".join(images))


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    icon_dir = repo_root / "assets" / "icon"
    iconset_dir = icon_dir / "9second_icon.iconset"
    generate_iconset(iconset_dir)
    generate_png(icon_dir / "icon_1024.png", 1024)

    # macOS: icns контейнер
    icon_icns = icon_dir / "icon.icns"
    generate_icns(iconset_dir, icon_icns)

    # Windows: ico контейнер
    icon_ico = icon_dir / "icon.ico"
    generate_ico(iconset_dir, icon_ico)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Post-process generated game art. Needs Pillow (pip install pillow).

    python postprocess.py key art/slime.png art/slime-alpha.png --color ff00ff
    python postprocess.py slice art/sheet.png art/frames --cols 4 --rows 2 --cell 256 --trim --anchor bottom
    python postprocess.py pixelate art/hero.png art/hero-64.png --size 64 --colors 16 --preview 8
    python postprocess.py tilecheck art/grass.png art/grass-2x2.png
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageChops, ImageStat


def key(src: str, dst: str, color: str = "ff00ff", tolerance: int = 60) -> Image.Image:
    """Turn a flat background color transparent, with a soft ramp so edges are not jagged."""
    target = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    image = Image.open(src).convert("RGBA")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            distance = ((r - target[0]) ** 2 + (g - target[1]) ** 2 + (b - target[2]) ** 2) ** 0.5
            if distance < tolerance:
                pixels[x, y] = (r, g, b, 0)
            elif distance < tolerance * 2:
                pixels[x, y] = (r, g, b, min(a, int(255 * (distance - tolerance) / tolerance)))
    image.save(dst)
    return image


def slice_sheet(src: str, out_dir: str, cols: int, rows: int, cell: int | None = None,
                trim: bool = False, anchor: str = "center") -> list:
    """Cut a grid sheet into equal cells. With trim, each cell is cropped to its opaque pixels (key the
    background first) and every frame is placed on the same canvas at the same scale, which evens out
    the uneven spacing image models produce without changing the character's size between frames."""
    image = Image.open(src).convert("RGBA")
    width, height = image.width // cols, image.height // rows
    frames = []
    for row in range(rows):
        for col in range(cols):
            frame = image.crop((col * width, row * height, (col + 1) * width, (row + 1) * height))
            box = frame.getchannel("A").getbbox() if trim else None
            frames.append(frame.crop(box) if box else frame)
    if cell:
        filled = [frame for frame in frames if frame.getchannel("A").getbbox()]
        scale = cell / max(max(frame.size) for frame in filled or frames)
        placed = []
        for frame in frames:
            if not frame.getchannel("A").getbbox():
                placed.append(Image.new("RGBA", (cell, cell), (0, 0, 0, 0)))
                continue
            frame = frame.resize((max(1, round(frame.width * scale)), max(1, round(frame.height * scale))), Image.LANCZOS)
            canvas = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
            x = (cell - frame.width) // 2
            y = cell - frame.height if anchor == "bottom" else (cell - frame.height) // 2
            canvas.paste(frame, (x, y), frame)
            placed.append(canvas)
        frames = placed
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(src))[0]
    paths = []
    for index, frame in enumerate(frames, 1):
        path = os.path.join(out_dir, f"{stem}_{index:02d}.png")
        frame.save(path)
        paths.append(path)
    return paths


def pixelate(src: str, dst: str, size: int, colors: int = 16, preview: int = 0) -> Image.Image:
    """Shrink a 'pixel art style' render to a real pixel grid and a fixed palette."""
    image = Image.open(src).convert("RGBA")
    scale = size / max(image.size)
    small = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.BOX)
    alpha = small.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    quantized = small.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    result = quantized.convert("RGBA")
    result.putalpha(alpha)
    result.save(dst)
    if preview:
        root, ext = os.path.splitext(dst)
        result.resize((result.width * preview, result.height * preview), Image.NEAREST).save(f"{root}@{preview}x{ext}")
    return result


def _column_gap(tile: Image.Image, a: int, b: int) -> float:
    left, right = tile.crop((a, 0, a + 1, tile.height)), tile.crop((b, 0, b + 1, tile.height))
    return sum(ImageStat.Stat(ImageChops.difference(left, right)).mean) / 3


def tilecheck(src: str, dst: str) -> float:
    """Write a 2x2 tiled preview and return the seam ratio: how much the wrap-around edges differ,
    relative to ordinary neighbouring columns and rows inside the tile. About 1 means seamless."""
    tile = Image.open(src).convert("RGB")
    preview = Image.new("RGB", (tile.width * 2, tile.height * 2))
    for x in (0, tile.width):
        for y in (0, tile.height):
            preview.paste(tile, (x, y))
    preview.save(dst)
    ratios = []
    for image in (tile, tile.transpose(Image.Transpose.ROTATE_90)):
        w = image.width
        seam = _column_gap(image, w - 1, 0)
        inside = sum(_column_gap(image, x, x + 1) for x in (w // 4, w // 2, 3 * w // 4)) / 3
        ratios.append(seam / max(inside, 0.5))
    return round(max(ratios), 2)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("key", help="flat background color -> transparency")
    p.add_argument("src"); p.add_argument("dst")
    p.add_argument("--color", default="ff00ff", help="hex of the background asked for in the prompt")
    p.add_argument("--tolerance", type=int, default=60)
    p = sub.add_parser("slice", help="cut a grid sheet into frames")
    p.add_argument("src"); p.add_argument("out_dir")
    p.add_argument("--cols", type=int, required=True); p.add_argument("--rows", type=int, required=True)
    p.add_argument("--cell", type=int, help="square output size in pixels")
    p.add_argument("--trim", action="store_true", help="crop each cell to its opaque pixels first")
    p.add_argument("--anchor", choices=("center", "bottom"), default="center", help="bottom keeps feet on one baseline")
    p = sub.add_parser("pixelate", help="snap to a real pixel grid and palette")
    p.add_argument("src"); p.add_argument("dst")
    p.add_argument("--size", type=int, required=True, help="longest edge in pixels, e.g. 32 or 64")
    p.add_argument("--colors", type=int, default=16)
    p.add_argument("--preview", type=int, default=0, help="also write an N-times nearest-neighbour enlargement")
    p = sub.add_parser("tilecheck", help="2x2 preview and seam score for a tile")
    p.add_argument("src"); p.add_argument("dst")
    args = parser.parse_args(argv)

    if args.command == "key":
        key(args.src, args.dst, args.color, args.tolerance)
    elif args.command == "slice":
        print("\n".join(slice_sheet(args.src, args.out_dir, args.cols, args.rows, args.cell, args.trim, args.anchor)))
    elif args.command == "pixelate":
        pixelate(args.src, args.dst, args.size, args.colors, args.preview)
    else:
        ratio = tilecheck(args.src, args.dst)
        print(f"seam ratio {ratio}: about 1 is seamless, well above 1 means the wrap shows; look at {args.dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

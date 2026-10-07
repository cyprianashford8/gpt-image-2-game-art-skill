#!/usr/bin/env python3
"""Generate or edit one game asset with GPT Image 2 and log what it cost.

Standard library only. Text-only requests go to /images/generations; with --ref (and optional --mask)
they go to /images/edits: local files as multipart image[] fields, URLs as JSON images[].image_url.

    export GPT_IMAGE_API_KEY=...                    # GPT_IMAGE_BASE_URL defaults to https://argolink.io/v1
    python gen_asset.py "slime enemy, side view, ..." --size 1024x1024 -n 4 --out art/drafts/slime
    python gen_asset.py "same slime, now jumping" --ref art/anchor/slime.png --out art/frames/slime-jump
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import struct
import sys
import time
import urllib.error
import urllib.request
import uuid

DEFAULT_BASE_URL = "https://argolink.io/v1"
MODELS = ("gpt-image-2", "gpt-image-2.5-flare", "gpt-image-2.5-sunburst")
PRICE = {"1K": 0.015, "2K": 0.015, "4K": 0.02}  # USD per returned image, checked 2026-10-07
USER_AGENT = "game-art-gpt-image-2/1.0"  # the default Python-urllib agent can be refused with a 403


def tier(width: int, height: int) -> str:
    edge = max(width, height)
    return "1K" if edge <= 1024 else "2K" if edge <= 2048 else "4K"


def dimensions(data: bytes) -> tuple:
    """(width, height, extension) for PNG, JPEG or WebP bytes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return (*struct.unpack(">II", data[16:24]), "png")
    if data[:4] == b"RIFF" and data[8:16] == b"WEBPVP8X":
        return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little"), "webp"
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] == 0xFF and 0xC0 <= data[i + 1] <= 0xCF and data[i + 1] not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[i + 5:i + 9])
                return width, height, "jpg"
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0] if data[i] == 0xFF else 1
    return 0, 0, "bin"


def is_url(value: str) -> bool:
    return value.startswith(("https://", "http://", "data:"))


def data_url(path: str) -> str:
    with open(path, "rb") as handle:
        return f"data:{mimetypes.guess_type(path)[0] or 'image/png'};base64,{base64.b64encode(handle.read()).decode()}"


def build_request(args) -> tuple:
    """(path, body bytes, content type) for the request the arguments describe."""
    fields = {"model": args.model, "prompt": args.prompt, "size": args.size, "quality": args.quality,
              "n": args.n, "response_format": "b64_json"}
    if not args.ref:
        return "/images/generations", json.dumps(fields).encode(), "application/json"
    local = [p for p in args.ref + ([args.mask] if args.mask else []) if not is_url(p)]
    if len(local) == len(args.ref) + (1 if args.mask else 0):
        boundary = uuid.uuid4().hex
        body = bytearray()
        for name, value in fields.items():
            body += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        files = [("image[]", p) for p in args.ref] + ([("mask", args.mask)] if args.mask else [])
        for name, path in files:
            with open(path, "rb") as handle:
                content = handle.read()
            body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                     f'filename="{os.path.basename(path)}"\r\n'
                     f"Content-Type: {mimetypes.guess_type(path)[0] or 'image/png'}\r\n\r\n").encode()
            body += content + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        return "/images/edits", bytes(body), f"multipart/form-data; boundary={boundary}"
    fields["images"] = [{"image_url": p if is_url(p) else data_url(p)} for p in args.ref]
    if args.mask:
        fields["mask"] = {"image_url": args.mask if is_url(args.mask) else data_url(args.mask)}
    return "/images/edits", json.dumps(fields).encode(), "application/json"


def send(path: str, body: bytes, content_type: str) -> list:
    api_key = os.environ.get("GPT_IMAGE_API_KEY")
    if not api_key:
        sys.exit("set GPT_IMAGE_API_KEY")
    base_url = (os.environ.get("GPT_IMAGE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    request = urllib.request.Request(base_url + path, data=body, method="POST")
    request.add_header("Authorization", f"Bearer {api_key}")
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("Content-Type", content_type)
    try:
        # The response arrives only when every image is finished; 2K and 4K take longer.
        with urllib.request.urlopen(request, timeout=600) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as error:
        sys.exit(f"{path} returned {error.code}: {error.read().decode(errors='replace')[:400]}")
    return [base64.b64decode(item["b64_json"]) for item in payload.get("data", [])]


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or edit a game asset with GPT Image 2.")
    parser.add_argument("prompt")
    parser.add_argument("--size", default="1024x1024", help="WIDTHxHEIGHT, e.g. 1024x1024, 2048x1152, 3840x2160")
    parser.add_argument("--quality", default="medium", choices=("auto", "low", "medium", "high"))
    parser.add_argument("-n", type=int, default=1, help="images in one request, 1-7, each billed")
    parser.add_argument("--model", default="gpt-image-2", choices=MODELS)
    parser.add_argument("--ref", action="append", default=[], help="reference image path or URL, up to 16")
    parser.add_argument("--mask", help="mask image (PNG with alpha), applied to the first reference")
    parser.add_argument("--out", default="art/asset", help="output path prefix, without extension")
    parser.add_argument("--log", default="art/assets.jsonl", help="JSONL log of every request")
    parser.add_argument("--dry-run", action="store_true", help="print the request instead of sending it")
    args = parser.parse_args(argv)

    if not 1 <= args.n <= 7:
        parser.error("-n must be 1-7")
    if len(args.ref) > 16:
        parser.error("an edit takes at most 16 reference images")
    if args.mask and not args.ref:
        parser.error("--mask needs at least one --ref")
    path, body, content_type = build_request(args)
    if args.dry_run:
        shown = body.decode(errors="replace") if content_type == "application/json" else f"<{len(body)} bytes multipart>"
        print(f"POST {path}\n{shown[:2000]}")
        return 0

    started = time.monotonic()
    images = send(path, body, content_type)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    files, cost = [], 0.0
    for index, image in enumerate(images, 1):
        width, height, extension = dimensions(image)
        target = f"{args.out}-{index}.{extension}" if len(images) > 1 else f"{args.out}.{extension}"
        with open(target, "wb") as handle:
            handle.write(image)
        cost += PRICE[tier(width, height)] if width else PRICE["1K"]
        files.append({"path": target, "pixels": f"{width}x{height}"})
        print(target)
    record = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "endpoint": path, "model": args.model, "prompt": args.prompt,
              "size": args.size, "quality": args.quality, "n": args.n, "refs": args.ref, "mask": args.mask,
              "files": files, "cost": round(cost, 4), "seconds": round(time.monotonic() - started, 1)}
    os.makedirs(os.path.dirname(args.log) or ".", exist_ok=True)
    with open(args.log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    print(f"{len(images)} image(s), about ${cost:.3f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

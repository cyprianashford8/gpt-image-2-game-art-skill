"""Offline tests for the skill's scripts. Requests are built but never sent; images are synthetic."""
import argparse
import json
import os
import sys

import pytest
from PIL import Image

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "skills", "game-art-gpt-image-2", "scripts")
sys.path.insert(0, SCRIPTS)
import gen_asset  # noqa: E402
import postprocess  # noqa: E402


def args(**overrides):
    base = dict(prompt="a slime", size="1024x1024", quality="medium", n=1, model="gpt-image-2", ref=[], mask=None)
    base.update(overrides)
    return argparse.Namespace(**base)


def test_text_only_goes_to_generations_as_json():
    path, body, content_type = gen_asset.build_request(args(n=4))
    assert (path, content_type) == ("/images/generations", "application/json")
    assert json.loads(body) == {"model": "gpt-image-2", "prompt": "a slime", "size": "1024x1024",
                                "quality": "medium", "n": 4, "response_format": "b64_json"}


def test_local_references_and_mask_go_as_multipart(tmp_path):
    anchor, mask = tmp_path / "anchor.png", tmp_path / "mask.png"
    anchor.write_bytes(b"ANCHOR")
    mask.write_bytes(b"MASK")
    path, body, content_type = gen_asset.build_request(args(ref=[str(anchor)], mask=str(mask)))
    assert path == "/images/edits" and content_type.startswith("multipart/form-data")
    assert b'name="image[]"; filename="anchor.png"' in body and b"ANCHOR" in body
    assert b'name="mask"; filename="mask.png"' in body


def test_url_references_go_as_json_image_url_objects():
    _, body, content_type = gen_asset.build_request(args(ref=["https://example.com/a.png"]))
    assert content_type == "application/json"
    assert json.loads(body)["images"] == [{"image_url": "https://example.com/a.png"}]


def test_tiers_and_header_dimensions(tmp_path):
    assert gen_asset.tier(1024, 1024) == "1K" and gen_asset.tier(2048, 1152) == "2K" and gen_asset.tier(3840, 2160) == "4K"
    target = tmp_path / "x.png"
    Image.new("RGB", (640, 360)).save(target)
    assert gen_asset.dimensions(target.read_bytes()) == (640, 360, "png")
    Image.new("RGB", (300, 200)).save(tmp_path / "x.jpg")
    assert gen_asset.dimensions((tmp_path / "x.jpg").read_bytes()) == (300, 200, "jpg")


def test_dry_run_sends_nothing(capsys, monkeypatch):
    monkeypatch.setattr(gen_asset.urllib.request, "urlopen", lambda *a, **k: pytest.fail("sent a request"))
    assert gen_asset.main(["icon of a potion", "--dry-run"]) == 0
    assert "POST /images/generations" in capsys.readouterr().out


def test_key_makes_the_flat_background_transparent(tmp_path):
    src = tmp_path / "sprite.png"
    image = Image.new("RGB", (40, 40), (255, 0, 255))
    image.paste((30, 160, 60), (10, 10, 30, 30))
    image.save(src)
    keyed = postprocess.key(str(src), str(tmp_path / "out.png"))
    assert keyed.getpixel((0, 0))[3] == 0
    assert keyed.getpixel((20, 20)) == (30, 160, 60, 255)


def test_slice_trims_and_keeps_one_scale_and_baseline(tmp_path):
    sheet = Image.new("RGBA", (400, 400), (0, 0, 0, 0))  # 4x2 cells of 100x200
    sheet.paste((200, 0, 0, 255), (20, 40, 60, 180))    # tall sprite in cell 1
    sheet.paste((0, 0, 200, 255), (130, 120, 170, 180))  # short sprite in cell 2
    sheet.save(tmp_path / "sheet.png")
    paths = postprocess.slice_sheet(str(tmp_path / "sheet.png"), str(tmp_path / "frames"), cols=4, rows=2,
                                    cell=70, trim=True, anchor="bottom")
    assert len(paths) == 8
    tall, short = Image.open(paths[0]), Image.open(paths[1])
    assert tall.size == short.size == (70, 70)
    assert tall.getchannel("A").getbbox()[3] == short.getchannel("A").getbbox()[3] == 70   # same baseline
    assert tall.getchannel("A").getbbox()[1] < short.getchannel("A").getbbox()[1]          # sizes preserved


def test_pixelate_snaps_size_and_palette(tmp_path):
    src = tmp_path / "hero.png"
    Image.effect_mandelbrot((512, 512), (-2, -1.5, 1, 1.5), 64).convert("RGBA").save(src)
    out = postprocess.pixelate(str(src), str(tmp_path / "hero-64.png"), size=64, colors=8, preview=4)
    assert out.size == (64, 64)
    assert len(out.convert("RGB").getcolors(64 * 64)) <= 8
    assert Image.open(tmp_path / "hero-64@4x.png").size == (256, 256)


def test_tilecheck_tells_seamless_from_seamed(tmp_path):
    seamless = Image.linear_gradient("L").resize((64, 64))
    seamless = Image.merge("RGB", [seamless.point(lambda v: 128)] * 3)  # flat: every boundary identical
    seamless.save(tmp_path / "flat.png")
    assert postprocess.tilecheck(str(tmp_path / "flat.png"), str(tmp_path / "flat-2x2.png")) <= 1
    Image.linear_gradient("L").resize((64, 64)).convert("RGB").save(tmp_path / "ramp.png")
    assert postprocess.tilecheck(str(tmp_path / "ramp.png"), str(tmp_path / "ramp-2x2.png")) > 10


def test_requests_name_the_client(monkeypatch):
    seen = []

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return json.dumps({"data": []}).encode()

    def urlopen(request, timeout=None):
        seen.append(request)
        return Reply()

    monkeypatch.setenv("GPT_IMAGE_API_KEY", "k")
    monkeypatch.setattr(gen_asset.urllib.request, "urlopen", urlopen)
    gen_asset.send("/images/generations", b"{}", "application/json")
    assert seen[0].get_header("User-agent") == gen_asset.USER_AGENT

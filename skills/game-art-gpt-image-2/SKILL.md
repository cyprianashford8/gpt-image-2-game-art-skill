---
name: game-art-gpt-image-2
description: Make 2D game art with GPT Image 2 and keep a set consistent - sprites and sprite sheets, animation frames, seamless tiles, item and ability icons, character turnarounds, UI panels, parallax backgrounds and pixel art. Use when the user asks for game assets, a sprite or sprite sheet, a tileset or texture, inventory icons, a character sheet, or wants existing art restyled or extended for a game. Not for 3D models, audio or video.
license: MIT
compatibility: Python 3.8+. scripts/gen_asset.py needs network access to an OpenAI-style Images API serving gpt-image-2 and a key in GPT_IMAGE_API_KEY; scripts/postprocess.py needs Pillow 9.1+.
---

# Game art with GPT Image 2

You produce game-ready 2D assets with GPT Image 2, then clean them up locally. The model paints at 1K or more; the game usually wants small, aligned, transparent pieces. Most of the work is in the brief, the reference loop and the post-processing, not in one perfect prompt.

## Workflow

1. **Pin the brief before the first request.** If `art/STYLE.md` does not exist, write it with the user (template below). Every prompt you send repeats its view, palette, outline, shading, light direction and background color.
2. **Choose size and tier** from the table below. Sprites and icons get downscaled anyway, so 1K is usually right.
3. **Draft wide.** One request with `-n 4` (up to 7) at quality `medium`. Show the user the drafts and let them pick.
4. **Lock the look.** Save the chosen draft as the anchor (`art/anchor/<name>.png`). From now on, every related asset is an *edit* that passes the anchor, plus up to 15 other approved assets, as references.
5. **Post-process** with `scripts/postprocess.py`: key out the flat background, slice sheets, snap pixel art, check tile seams.
6. **Log and name.** `scripts/gen_asset.py` appends every request (prompt, size, quality, refs, files, cost) to `art/assets.jsonl`. Name outputs `<kind>-<name>-<variant>`, e.g. `icon-potion-red`.

## STYLE.md template

```markdown
View: side-on platformer | top-down 3/4 | isometric 2:1
Target size in engine: 64x64 sprites, 32x32 tiles, 128x128 icons
Palette: #1b1b2f #3f3f74 #6b8e23 #f2d16b #f7f3e3 (max 16 colors for pixel art)
Outline: 2 px dark outline | none
Shading: two-tone cel | soft painterly
Light: from the top-left
Background for keying: flat #FF00FF, no shadow, no gradient, no floor
Never: text, watermarks, UI frames, cast shadows on the background
```

## Size and tier

The tier is the longest edge of the image you get back: up to 1024 is 1K, 1025–2048 is 2K, above 2048 is 4K. Write the size as pixels (`1024x1024`), never as `1K` or `16:9`, and also say the ratio in the prompt ("square 1:1 composition").

| Asset | Size | Tier | Why |
|---|---|---|---|
| One sprite, icon, item, portrait | `1024x1024` | 1K | ends up at 32–256 px; more pixels buy nothing |
| Sprite sheet 4×2, icon sheet 4×4 | `2048x1152` or `1440x1440` | 2K | each cell keeps 300+ px of detail |
| Turnaround (front, 3/4, side, back) | `2048x878` (21:9) | 2K | four full-body views in a row |
| Seamless tile or texture | `1024x1024` | 1K | tile it in the engine |
| Background, parallax layer, key art | `3840x2160` or `3840x1646` | 4K | the only assets shown large |

On the default endpoint 1K and 2K cost $0.015 per returned image and 4K $0.02, whatever the `quality`, so use `high` for finals: it costs the same and only takes longer. Every image of `-n` is billed.

## Rules by asset type

Recipes with full prompts are in `references/asset-recipes.md`. The short version:

- **Sprites**: one subject, full body, centered, feet on the bottom third line, flat key background, no ground shadow. Say the view ("side view facing right").
- **Sprite sheets and animation frames**: ask for "a 4 by 2 grid of equal cells, one pose per cell, same character, same scale, same baseline, thin empty gutters, no grid lines, no numbers". The model never spaces cells exactly, so always run `postprocess.py slice --trim --anchor bottom` after keying. For animation, generate frames as edits from the anchor ("frame 3 of 6 of a run cycle") instead of trusting one sheet to stay consistent.
- **Tiles**: "seamless tileable texture, top-down orthographic, even lighting, no vignette, no perspective, edges continue across the borders". Check with `postprocess.py tilecheck` and look at the 2×2 preview. Generate transitions (grass to sand) as separate tiles; full autotile sets are better finished in a tile editor.
- **Icons**: same frame, size, light and palette for the whole set. Make one anchor icon, then each new icon is an edit with the anchor and 2–4 approved icons as references: "same style and frame as the reference icons; new subject: a blue mana potion".
- **Characters**: start with a turnaround sheet, approve it, then use it as the reference for portraits, poses and frames. Describe the character the same way every time (copy the sentence).
- **UI**: front-on and flat, uniform border thickness, plain center, so it can be 9-sliced. Leave labels out and render text in the engine.
- **Backgrounds and parallax**: one layer per request; every layer except the farthest goes on the flat key color so it can be cut out.
- **Pixel art**: the model's "pixels" are not on a grid. Generate at 1K with "pixel art, limited palette", then `postprocess.py pixelate --size 64 --colors 16 --preview 8` and review the enlarged preview.

## Consistency

- References beat adjectives. Pass the anchor and the closest approved assets (1–16 images per edit) and say what to keep: "keep the character's proportions, outfit colors and outline from the references".
- A mask (PNG with an alpha channel, same size as the first reference) limits a change to one area: recolor a cape, swap a weapon. Masking is guided by the prompt, so the edit may not follow the mask edge exactly; key or crop afterwards if it spills.
- Repeat the STYLE.md block verbatim in every prompt. Change one thing per iteration.
- Describe a style in visual terms (palette, line weight, shading, era of hardware) rather than naming a franchise or a living artist.

## API facts (default endpoint)

| | |
|---|---|
| Base URL | `https://argolink.io/v1` (override with `GPT_IMAGE_BASE_URL`) |
| Text to image | `POST /images/generations`: `model`, `prompt`, `size`, `quality` (`auto`, `low`, `medium`, `high`), `n` 1–7, `response_format` (`url` or `b64_json`) |
| Edit | `POST /images/edits`: the same fields plus 1–16 references, as JSON `images: [{"image_url": …}]` (HTTPS or data URL) or multipart `image[]` files; optional `mask` (`mask.image_url` in JSON, a `mask` file in multipart) |
| Models with the same fields | `gpt-image-2`, `gpt-image-2.5-flare` (fast everyday), `gpt-image-2.5-sunburst` (precise edits) |
| Background | no transparency parameter is documented on this route: ask for a flat key color and use `postprocess.py key` |
| Waiting | the call returns when every image is done; allow 600 s |

## Scripts

```bash
# Draft four options for a new enemy
python scripts/gen_asset.py "Slime enemy, side view facing right, ... flat #FF00FF background, square 1:1 composition" \
  --size 1024x1024 -n 4 --out art/drafts/slime

# Extend the set from the approved anchor
python scripts/gen_asset.py "Same slime as the reference, squashed flat mid-bounce ..." \
  --ref art/anchor/slime.png --quality high --out art/frames/slime-bounce

# Clean up
python scripts/postprocess.py key art/frames/slime-bounce.png art/frames/slime-bounce-alpha.png --color ff00ff
python scripts/postprocess.py slice art/sheets/slime-run.png art/frames/run --cols 4 --rows 2 --cell 128 --trim --anchor bottom
python scripts/postprocess.py tilecheck art/tiles/grass.png art/tiles/grass-2x2.png
```

`gen_asset.py --dry-run` prints the request without sending it. Both scripts exit non-zero with the API's message on errors; show that message to the user rather than retrying blindly.

## Before you hand assets over

- [ ] Background keyed, no magenta fringe left (zoom in on edges).
- [ ] Frames share scale and baseline; tiles pass the 2×2 check by eye.
- [ ] Sizes match STYLE.md; pixel art enlarged with nearest-neighbour only.
- [ ] `art/assets.jsonl` has the prompt and references for every delivered file, and you told the user what the session cost.

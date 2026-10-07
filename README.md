# GPT Image 2 game art skill — sprites, tiles, icons and sheets for Claude Code and Codex

An agent skill that teaches a coding agent to make 2D game assets with GPT Image 2 and keep them consistent: a style brief, a draft-then-anchor loop built on reference edits, size and tier rules, ten asset recipes, and two scripts that call the API and clean up the results (key out the background, slice sheets, snap pixel art, check tile seams).

| Part | Kind | What it does |
| :--- | :--- | :--- |
| [game-art-gpt-image-2](./skills/game-art-gpt-image-2/SKILL.md) | Skill | Workflow, STYLE.md template, size/tier table, rules per asset type, consistency rules, API facts, hand-over checklist |
| [asset-recipes.md](./skills/game-art-gpt-image-2/references/asset-recipes.md) | Reference | 10 recipes (enemy sprite, frame-by-frame cycle, one-shot sheet, icon set, seamless tile, turnaround, portrait, 9-slice panel, parallax layer, pixel item) with settings and cost |
| [gen_asset.py](./skills/game-art-gpt-image-2/scripts/gen_asset.py) | Script | Generate, or edit with up to 16 references and a mask; saves files and logs prompt, refs and cost to `art/assets.jsonl` |
| [postprocess.py](./skills/game-art-gpt-image-2/scripts/postprocess.py) | Script | `key` flat background to alpha, `slice` sheets with trim and one baseline, `pixelate` to a grid and palette, `tilecheck` seams |

<sub>Last checked: 2026-10-07 (API fields, limits and prices in the skill).</sub>

## Install

```bash
git clone https://github.com/cyprianashford8/gpt-image-2-game-art-skill
cd gpt-image-2-game-art-skill
pip install pillow                          # for postprocess.py
```

| Agent | Copy the skill folder to | Invoke |
|---|---|---|
| Claude Code, every project | `~/.claude/skills/game-art-gpt-image-2/` | ask for game art, or `/game-art-gpt-image-2` |
| Claude Code, one project | `<project>/.claude/skills/game-art-gpt-image-2/` | same |
| Codex CLI / IDE extension | `~/.agents/skills/game-art-gpt-image-2/` or `<repo>/.agents/skills/…` | ask, or `$game-art-gpt-image-2` |
| Any Agent Skills host | wherever it loads skills | the frontmatter uses only the standard fields |

```bash
cp -r skills/game-art-gpt-image-2 ~/.claude/skills/      # Claude Code
cp -r skills/game-art-gpt-image-2 ~/.agents/skills/      # Codex
```

Then give the scripts a key:

```bash
export GPT_IMAGE_API_KEY=your-key                       # get one at argolink.io
# export GPT_IMAGE_BASE_URL=https://argolink.io/v1     # the default; any OpenAI-style Images API
```

The default endpoint is [ArgoLink](https://argolink.io/gh-gpt-image-2-game-art-skill), where GPT Image 2 costs $0.015 per image at 1K or 2K and $0.02 at 4K whatever the quality, which is why the skill drafts several options per request and renders finals at `high`.

## Try it

Ask your agent things like:

- "Make a side-view slime enemy for my platformer, then a 6-frame bounce cycle that matches it."
- "I need 24 inventory icons in the same style as `art/icons/potion.png`."
- "Generate a seamless cobblestone tile for a top-down RPG and check that it tiles."
- "Turn this character concept into a front / 3/4 / side / back turnaround."
- "Make a 32×32 pixel-art coin and gem for the HUD."

The skill writes `art/STYLE.md` with you first (view, engine size, palette, outline, shading, light, key color), drafts 3–4 options, saves the one you pick as an anchor, and builds every related asset as an edit of that anchor.

## What the skill insists on

- **Pixels in `size`, the ratio in words.** `size` is `WIDTHxHEIGHT`; the prompt also says "square 1:1 composition" or "21:9 composition".
- **A flat key color instead of transparency.** No transparency parameter is documented on the default route, so assets are painted on flat `#FF00FF` and keyed locally, with a soft edge ramp.
- **References over adjectives.** Up to 16 approved images per edit, with the anchor first; a mask confines a change to one area.
- **Frames from the anchor, not from luck.** One-shot sprite sheets drift; frame-by-frame edits from the anchor stay on model. Sheets are always re-aligned with `slice --trim --anchor bottom`.
- **A receipt.** Every request is logged with its cost, and the agent tells you the session total.

## Script reference

```bash
python skills/game-art-gpt-image-2/scripts/gen_asset.py PROMPT \
  [--size 1024x1024] [--quality auto|low|medium|high] [-n 1-7] \
  [--model gpt-image-2|gpt-image-2.5-flare|gpt-image-2.5-sunburst] \
  [--ref PATH_OR_URL ...] [--mask PATH] [--out art/asset] [--log art/assets.jsonl] [--dry-run]

python skills/game-art-gpt-image-2/scripts/postprocess.py key SRC DST [--color ff00ff] [--tolerance 60]
python skills/game-art-gpt-image-2/scripts/postprocess.py slice SRC OUT_DIR --cols C --rows R [--cell PX] [--trim] [--anchor center|bottom]
python skills/game-art-gpt-image-2/scripts/postprocess.py pixelate SRC DST --size PX [--colors 16] [--preview 8]
python skills/game-art-gpt-image-2/scripts/postprocess.py tilecheck SRC PREVIEW
```

`tilecheck` prints a seam ratio: the wrap-around edge difference divided by the difference between ordinary neighbouring columns and rows inside the tile. Around 1 the seam is invisible; well above 1 it shows in the 2×2 preview.

## What a set costs

Icons at 1024×1024, two options each, so 80 images for a 40-icon inventory:

| Where | Per image | 40-icon set |
|---|---:|---:|
| ArgoLink, any quality | $0.015 | **$1.20** |
| OpenAI API, `medium` | $0.053 | $4.24 |
| OpenAI API, `high` | $0.211 | $16.88 |
| Replicate, `high` | $0.128 | $10.24 |

<sub>Checked 2026-10-07: [ArgoLink GPT Image 2 page](https://argolink.io/en/models/gpt-image-2); OpenAI's per-image figures from the [image generation guide](https://developers.openai.com/api/docs/guides/image-generation) (output tokens only; prompt and reference-image tokens are extra, and edits with references add input tokens); [Replicate openai/gpt-image-2](https://replicate.com/openai/gpt-image-2).</sub>

## FAQ

**Can GPT Image 2 make real pixel art?**
It makes images that look like pixel art, but its "pixels" don't sit on a grid and the palette drifts. Generate at 1K, then run `postprocess.py pixelate --size 32 --colors 16` and touch up the result; at 32 px that is a few minutes of hand work.

**How do I keep a character consistent across animation frames?**
Approve one anchor image, then make each frame as an edit with the anchor as the first reference and the frame described by number and pose ("frame 3 of 6, landing, squashed flat"). Add already-approved frames as extra references; an edit takes up to 16.

**Why not ask for a transparent background?**
The default endpoint documents no transparency parameter for GPT Image 2, so the skill doesn't rely on one. A flat magenta that appears nowhere in the art keys out cleanly, and `key` ramps the edge so outlines don't go jagged.

**Which tier should sprites use?**
1K (`1024x1024`). A sprite shown at 64 px gains nothing from 2K. Use 2K for multi-cell sheets and 4K only for backgrounds and key art.

**Does it work with GPT Image 2.5?**
Yes: pass `--model gpt-image-2.5-flare` or `gpt-image-2.5-sunburst`. On the default endpoint they take the same fields at the same price; Sunburst is described there as the precision editing model.

## Tests

```bash
pip install pytest pillow
pytest tests/
```

Requests are built but never sent, and the images are synthetic, so the tests need no key.

## License

MIT. An independent skill, not affiliated with OpenAI or Anthropic.

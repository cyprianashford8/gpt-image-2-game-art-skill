# Asset recipes

Each recipe is a prompt you adapt, the request settings, what it costs on the default endpoint ($0.015 per returned image at 1K/2K, $0.02 at 4K, any quality) and the clean-up step. Replace the `{STYLE}` line with the block from `art/STYLE.md`.

## 1. Side-view enemy sprite (draft round)

```text
{STYLE}
A round green slime enemy for a side-scrolling platformer, side view facing right, two small
dark eyes, a glossy highlight on top, full body centered, resting on the lower third of the frame.
Flat #FF00FF background, no ground, no shadow, no text. Square 1:1 composition.
```

`--size 1024x1024 --quality medium -n 4` → 4 drafts, $0.06. Then `postprocess.py key` on the one you keep and save it as `art/anchor/slime.png`.

## 2. Run cycle from an anchor (one frame per request)

```text
{STYLE}
The same slime as the reference image, same colors, outline and size. Frame 3 of a 6-frame
bounce cycle: body squashed wide and flat as it lands. Side view facing right. Flat #FF00FF
background, no shadow. Square 1:1 composition.
```

`--ref art/anchor/slime.png --size 1024x1024 --quality high -n 2` per frame → 6 frames × 2 options = 12 images, $0.18. Key each frame, then line them up with `slice` on a sheet or by hand in the engine.

## 3. Sprite sheet in one request (fast, less consistent)

```text
{STYLE}
A sprite sheet of a knight walking, side view facing right, 4 columns by 2 rows of equal cells,
one pose per cell in walk-cycle order from left to right, top row then bottom row. Same knight,
same scale and the same baseline in every cell, thin empty gutters, no grid lines, no numbers.
Flat #FF00FF background. 16:9 composition.
```

`--size 2048x1152 --quality high -n 3` → $0.045. Then `key`, then `slice --cols 4 --rows 2 --cell 128 --trim --anchor bottom`.

## 4. Inventory icon set

Anchor first:

```text
{STYLE}
Inventory icon of a red health potion: round glass flask with a cork, centered, filling about
70% of the frame, inside a dark rounded-square frame with a 4 px gold border. Light from the
top-left. Plain #FF00FF outside the frame. Square 1:1 composition.
```

Then each icon is an edit with the anchor plus 2–4 approved icons:

```text
Same frame, border, lighting, palette and rendering as the reference icons.
New subject: a blue mana potion in a tall thin bottle.
```

`--ref art/anchor/icon-potion-red.png --ref art/icons/icon-key.png --size 1024x1024 -n 2` → $0.03 per icon.

## 5. Seamless ground tile

```text
{STYLE}
Seamless tileable texture of short grass with a few clover leaves, top-down orthographic view,
even flat lighting, no vignette, no perspective, no large unique features, details continue
across all four edges. Square 1:1 composition.
```

`--size 1024x1024 --quality high -n 3` → $0.045. Run `postprocess.py tilecheck` on each; keep the one whose ratio is closest to 1 and whose 2×2 preview shows no grid.

## 6. Character turnaround

```text
{STYLE}
Character turnaround sheet of a young alchemist: front view, three-quarter view, side view and
back view in one row, left to right, evenly spaced. Full body, neutral A-pose, identical
proportions, outfit and colors in every view, all feet on one baseline. Leather apron over a
green tunic, brass goggles on the forehead, satchel on the left hip. Flat #FF00FF background,
no labels. 21:9 composition.
```

`--size 2048x878 --quality high -n 2` → $0.03. Approve one; it becomes the reference for portraits, poses and frames.

## 7. Dialogue portrait from the turnaround

```text
Bust portrait of the character in the reference sheet, same face, hair, goggles and outfit
colors. Three-quarter view facing left, friendly smile. {STYLE} Flat #FF00FF background.
Square 1:1 composition.
```

`--ref art/anchor/alchemist-turnaround.png --size 1024x1024 -n 3` → $0.045.

## 8. Nine-slice UI panel

```text
A game UI dialogue panel, front-on and perfectly flat, dark walnut wood with brass corner
brackets, uniform 24 px border on all four sides, plain dark center with no texture or text,
centered in the frame. Flat #FF00FF background. Square 1:1 composition.
```

`--size 1024x1024 --quality high -n 2` → $0.03. Key it, then set the 9-slice margins in the engine at the border width you see.

## 9. Parallax layer

```text
{STYLE}
Middle parallax layer for a forest level: a row of dark pine silhouettes of varied height along
the bottom half, nothing in the sky. Everything that is not a tree is flat #FF00FF.
21:9 composition.
```

`--size 3840x1646 --quality high` → $0.02. Key it. Make the far layer (sky and mountains) without key color and the near layer (grass, rocks) with it.

## 10. Pixel-art item

```text
Pixel art of a gold coin with a star stamped on it, 16-color palette, hard edges, no
anti-aliasing, centered, flat #FF00FF background. Square 1:1 composition.
```

`--size 1024x1024 -n 4` → $0.06. Then `key`, then `pixelate --size 32 --colors 16 --preview 8`, and check the enlarged preview: fix stray pixels by hand, a 32 px sprite is quick to touch up.

## Costs at a glance

| Recipe | Images | Cost |
|---|---:|---:|
| 1 Enemy drafts | 4 | $0.06 |
| 2 Six-frame cycle, 2 options each | 12 | $0.18 |
| 3 One-shot sheet, 3 tries | 3 | $0.045 |
| 4 Icon, 2 options | 2 | $0.03 |
| 6 Turnaround, 2 options | 2 | $0.03 |
| 9 4K parallax layer | 1 | $0.02 |

A 40-icon inventory at two options per icon is 80 images, $1.20.

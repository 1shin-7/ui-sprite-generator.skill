---
name: ui-sprite-generator
description: Use when reconstructing a game UI mockup into a background plate, high-resolution UI sprite atlases, sliced PNG assets, and static Playwright-capturable HTML
---

# UI Sprite Generator

## Overview

Reconstruct a game UI effect image into a complete static scene for Playwright screenshots. The skill separates reusable skill files from per-run artifacts: prompts, scripts, and schemas live in the skill install directory; every generated file goes into an invocation run directory.

## Run Directory

Create or reuse a run directory in the caller's current workspace:

```text
ui-sprite-runs/YYYY-MM-DD-slug/
  input/effect.png
  spec.json
  background_plate.png
  atlas/*.png
  atlas_map.json
  sprites/*.png
  html/index.html
  screenshots/final.png
```

Never write run artifacts into the skill install directory, `.agents/skills`, or `.codex/skills`.

## Workflow

1. **Extract spec** with `prompts/01_extract_spec.md`.
   Output `spec.json`. This is the only semantic contract: source canvas, global style, background occlusion, components, source bboxes, resolution policy, atlas policy, layering, and render patterns.

2. **Generate background plate** with `prompts/02_generate_background_plate.md`.
   Output `background_plate.png`. This step is mandatory. Preserve visible background regions and infer UI-occluded regions by inpainting or generation. Do not create a stable background report JSON.

3. **Generate UI atlases** with `prompts/03_generate_ui_atlas.md`.
   Output one or more game-ready atlas PNGs under `atlas/`. Prefer `1536x1024` or `1024x1536`, but do not force all sprites into fixed canvas sizes. Each sprite must reach at least its source component resolution; default generation scale is 2x, with 3x for complex materials when practical. Do not downscale sprites to improve packing.

4. **Extract atlas map** with `prompts/04_extract_atlas_map.md`.
   Output `atlas_map.json`. This is the only coordinate contract: atlas files, sprite crop bboxes, output filenames, display sizes, z-index, and render-pattern parameters.

5. **Slice sprites** with `scripts/ui_slice.py`.
   The slicer is mechanical: it validates inputs, crops bboxes, optionally removes border-connected background, and writes `sprites/*.png`. It does not infer, confirm, correct, generate reports, or draw debug overlays.

6. **Generate Playwright HTML** with `prompts/05_generate_playwright_html.md`.
   Output `html/index.html`. Use static Jinja-style HTML/CSS with `background_plate.png` behind absolutely positioned sprites. The page serves Playwright screenshots only. JavaScript is limited to `window.__UI_READY__ = true` and optional `?debug=1` overlay. If static rendering fails, ask before injecting temporary JS patches.

## Stable Contracts

Keep only two stable JSON files:

| File | Purpose |
| --- | --- |
| `spec.json` | Semantic UI, background, component, resolution, atlas, and rendering intent |
| `atlas_map.json` | Atlas file and crop coordinates, sliced filename, display size, z-index, and render parameters |

Do not promote `sheet_plan.json`, `background_report.json`, `slice_report.json`, or `render_report.json` to stable contracts.

## Slicer

```bash
python scripts/ui_slice.py \
  --map ui-sprite-runs/YYYY-MM-DD-slug/atlas_map.json \
  --out ui-sprite-runs/YYYY-MM-DD-slug/sprites \
  --bg-policy keep
```

Optional white or gray background cleanup:

```bash
python scripts/ui_slice.py \
  --map ui-sprite-runs/YYYY-MM-DD-slug/atlas_map.json \
  --out ui-sprite-runs/YYYY-MM-DD-slug/sprites \
  --bg-policy transparentize-border \
  --bg-color auto \
  --bg-tolerance 18
```

`transparentize-border` removes only pixels connected to the crop border and near the detected background color. It must not delete all matching white pixels globally, because white may be part of the item material.

## External Image Generation Fallback

Use this only when the current environment has no available image generation service for the mandatory background plate or UI atlas steps. Ask the user before calling any external service.

Before continuing, request the image API base URL, model or endpoint shape, and API key delivery method. Explain that the token and uploaded effect image will be exposed to the tool execution environment and the configured image service. Recommend a temporary, low-scope, revocable API key.

Prefer passing the API key through an environment variable. Never write the token to the repo, run directory, prompt files, generated HTML, logs, schemas, or screenshots. Do not echo authorization headers. If the request fails, report only the status code and error category.

Use `xh` or `curl` only after the user has confirmed the service and upload scope. Save generated images into the invocation run directory. Large images should be referenced by path by default; show an inline image only for useful review, and prefer a downsampled thumbnail over embedding full-size output in the conversation.

## Common Mistakes

| Mistake | Correction |
| --- | --- |
| Writing generated files beside `SKILL.md` | Put them in the invocation run directory |
| Treating fixed atlas sizes as hard limits | Preserve sprite resolution and split atlases instead |
| Making Phase 4 a general JS runtime | Generate static HTML for Playwright; JS is a last-resort patch |
| Letting the slicer fix coordinates | Fix `atlas_map.json`; the slicer should fail on bad bboxes |
| Debugging atlas crops in the slicer | Use final HTML `?debug=1` overlay for render/debug inspection |

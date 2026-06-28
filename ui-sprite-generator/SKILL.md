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

Create `ui-sprite-runs/.gitignore` from `templates/runs.gitignore` before any credential prompt. Use `ui-sprite-runs/.env` as the shared image API configuration across runs. Use `ui-sprite-runs/YYYY-MM-DD-slug/.env` only when a specific run needs an override.

Do not ask the user to edit a non-existent .env path. If credentials are needed and `ui-sprite-runs/.env` is missing, create `ui-sprite-runs/`, copy `config/image-api.env.example` to `ui-sprite-runs/.env`, ensure `ui-sprite-runs/.gitignore` exists, then report the exact created path for the user to edit.

## Workflow

1. **Extract spec** with `prompts/01_extract_spec.md`.
   Output `spec.json`. This is the only semantic contract: source canvas, global style, background occlusion, components, source bboxes, resolution policy, atlas policy, layering, and render patterns.

2. **Generate background plate** with `prompts/02_generate_background_plate.md`.
   Output `background_plate.png`. This step is mandatory. Preserve visible background regions and infer UI-occluded regions by inpainting or generation. Do not create a stable background report JSON.

3. **Generate UI atlases** with `prompts/03_generate_ui_atlas.md`.
   First generate the formal Markdown prompt artifact with `scripts/build_atlas_prompt.py --spec ui-sprite-runs/YYYY-MM-DD-slug/spec.json --output ui-sprite-runs/YYYY-MM-DD-slug/prompts/ui_atlas.md`. Do not handwrite `ui_atlas.md`, do not summarize the canonical prompt, and do not replace it with a shorter natural-language prompt. Then pass that Markdown file to the image generation helper. Output one or more game-ready atlas PNGs under `atlas/`. Prefer `1536x1024` or `1024x1536`, but do not force all sprites into fixed canvas sizes. Each sprite must reach at least its source component resolution; default generation scale is 2x, with 3x for complex materials when practical. Do not downscale sprites to improve packing.

4. **Verify UI atlases** with `prompts/04_verify_ui_atlas.md`.
   Check each generated atlas before mapping. If QA reports missing components, wrong center semantics, invented internal texture, missing decoration, source background pixels, clipped ornament, or flat bar fill, rebuild `ui_atlas.md` with `scripts/build_atlas_prompt.py --component-id <id>` or `--component-group <group>` and regenerate the failed subset.

5. **Extract atlas map** with `prompts/04_extract_atlas_map.md`.
   Output `atlas_map.json`. This is the only coordinate contract: atlas files, sprite crop bboxes, output filenames, display sizes, z-index, and render-pattern parameters.

6. **Slice sprites** with `scripts/ui_slice.py`.
   The slicer is mechanical: it validates inputs, crops bboxes, optionally removes border-connected background, and writes `sprites/*.png`. It does not infer, confirm, correct, generate reports, or draw debug overlays.

7. **Generate Playwright HTML** with `prompts/05_generate_playwright_html.md`.
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

### Generation Capability Gate

Run this gate before Phase 2 or Phase 3. Only generative image services count: an available imagegen tool, a configured OpenAI-compatible endpoint, or an external generation/edit service explicitly confirmed by the user. Do not check local image-processing tools as substitutes. Pillow/OpenCV/canvas/crop are reference preparation only; they may prepare masks, prompts, contact sheets, or debug overlays, but they do not satisfy the generation requirement.

If no generative service is available, stop and configure the external image API. Create `ui-sprite-runs/.gitignore` and `ui-sprite-runs/.env` first if they do not exist, then ask the user to edit the created `ui-sprite-runs/.env`. Do not continue into spec-to-atlas production, deterministic slicing, or HTML reconstruction while waiting for generation credentials.

Use this only when the current environment has no available image generation service for the mandatory background plate or UI atlas steps. Phase 2 and Phase 3 are mandatory generation steps; local image processing may prepare masks, prompts, or validation, but it must not replace image generation.

Do not take a token-saving shortcut. "Usable result", "fast delivery", "no built-in image tool", or "preserve original style" is not a reason to replace generation with deterministic component slicing. Absolute-positioned HTML reconstruction from crops is an invalid substitute for this workflow: it produces dirty rectangular cutouts, mixed background pixels, clipped decoration, and fixed ugly corners on complex UI deco.

Ask the user before calling any external service. Before continuing, request the image API base URL, model or endpoint shape, and API key delivery method. Explain that the token and uploaded effect image will be exposed to the tool execution environment and the configured image service. Recommend a temporary, low-scope, revocable API key.

Create a shared `ui-sprite-runs/.env` from `config/image-api.env.example` and prompt the user to edit that file. A run-local `.env` may override it only for a single invocation. The .env file is the preferred environment variable source for `scripts/openai_image.py`. This avoids pasting API keys into prompts and avoids visible shell commands with tokens. Do not paste API keys into prompts, generated scripts, command arguments, logs, schemas, screenshots, or HTML. Do not commit `.env` files.

Use `scripts/openai_image.py` for OpenAI-compatible image generation or edit endpoints. The script reads `IMAGE_API_BASE_URL`, `IMAGE_API_KEY`, `IMAGE_API_MODEL`, `IMAGE_API_SIZE`, `IMAGE_API_QUALITY`, `IMAGE_API_RESPONSE_FORMAT`, and `IMAGE_API_TIMEOUT` from the environment, explicit `--env-file`, or `--run-dir` env lookup. With `--run-dir ui-sprite-runs/YYYY-MM-DD-slug`, it reads `ui-sprite-runs/.env` first and then `ui-sprite-runs/YYYY-MM-DD-slug/.env` for overrides. It also accepts non-secret `--base-url` overrides, but it does not accept an API key argument. It handles JSON `/images/generations`, multipart `/images/edits`, repeated `--input-image` fields, timeout, HTTP response status errors, JSON response parsing, `b64_json` output, image URL output, and output file creation.

Example:

```bash
mkdir -p ui-sprite-runs/YYYY-MM-DD-slug
cp .agents/skills/ui-sprite-generator/templates/runs.gitignore ui-sprite-runs/.gitignore
cp .agents/skills/ui-sprite-generator/config/image-api.env.example ui-sprite-runs/.env
python .agents/skills/ui-sprite-generator/scripts/openai_image.py \
  --run-dir ui-sprite-runs/YYYY-MM-DD-slug \
  --prompt-file ui-sprite-runs/YYYY-MM-DD-slug/prompts/background_plate.txt \
  --mode edits \
  --input-image ui-sprite-runs/YYYY-MM-DD-slug/input/effect.png \
  --output ui-sprite-runs/YYYY-MM-DD-slug/background_plate.png
```

For a pure text-to-image generation endpoint, omit `--input-image` and use `--mode generations` or `--mode auto` with a `/images/generations` base URL. For an edit endpoint, use `--mode edits` and pass each source/reference/mask image with a separate `--input-image`; the helper sends repeated multipart `image` fields.

After the user confirms an external image API, do not substitute local Pillow, OpenCV, screenshot crop, mask-fill, or segmentation-only output for Phase 2 or Phase 3. You must either call the confirmed external image API through `scripts/openai_image.py` or stop and ask the user to finish `.env` configuration. Do not continue with local segmentation as a replacement for generation.

Local crops are analysis reference only: bbox review, mask preparation, prompt references, contact sheets, or debug overlays. They are not formal atlas art, not a completed background plate, and not acceptable inputs to the final slicer except as non-output references for image generation.

If a user pasted an API key directly into chat, do not reuse it in a visible shell command. State the exposure risk, recommend rotating it, then ask the user to place the replacement key in `ui-sprite-runs/.env` unless this run deliberately needs a run-local override. If an image request fails, report only the timeout, response status, or error category; never echo authorization headers.

Save generated images into the invocation run directory. Large images should be referenced by path by default; show an inline image only for useful review, and prefer a downsampled thumbnail over embedding full-size output in the conversation.

## Common Mistakes

| Mistake | Correction |
| --- | --- |
| Writing generated files beside `SKILL.md` | Put them in the invocation run directory |
| Treating fixed atlas sizes as hard limits | Preserve sprite resolution and split atlases instead |
| Making Phase 4 a general JS runtime | Generate static HTML for Playwright; JS is a last-resort patch |
| Letting the slicer fix coordinates | Fix `atlas_map.json`; the slicer should fail on bad bboxes |
| Debugging atlas crops in the slicer | Use final HTML `?debug=1` overlay for render/debug inspection |
| Replacing Phase 2 or Phase 3 with local segmentation | Stop and call `scripts/openai_image.py`, or ask the user to finish `ui-sprite-runs/.env` configuration |
| Shipping deterministic component slicing as a "usable result" | Treat it as invalid; crops are analysis reference only, not formal atlas art |
| Handwriting a short atlas prompt | Use `scripts/build_atlas_prompt.py` to generate `ui_atlas.md` |

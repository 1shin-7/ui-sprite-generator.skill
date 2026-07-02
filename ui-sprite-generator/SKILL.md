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
  effect.png
  spec.yaml
  background_plate.png
  render.yaml
  index.html
  final.png
  atlas/*.png
  atlas/*.map.yaml
  sprites/*.png
```

Never write run artifacts into the skill install directory, `.agents/skills`, or `.codex/skills`.

Create `ui-sprite-runs/.gitignore` from `templates/runs.gitignore` before any credential prompt. Use `ui-sprite-runs/.env` as the shared image API configuration across runs. Use `ui-sprite-runs/YYYY-MM-DD-slug/.env` only when a specific run needs an override.

Do not ask the user to edit a non-existent .env path. If credentials are needed and `ui-sprite-runs/.env` is missing, create `ui-sprite-runs/`, copy `config/image-api.env.example` to `ui-sprite-runs/.env`, ensure `ui-sprite-runs/.gitignore` exists, then report the exact created path for the user to edit.

## Progressive Reading

Read only the prompt for the current phase. After completing a phase and writing or verifying its output, read the next phase prompt. Do not preload every prompt, schema, or script source when the skill starts. Use helper CLIs and `--help` during normal execution; do not preload script source unless you are changing a helper, debugging unexpected behavior, or validating security-sensitive behavior.

## Workflow

1. **Extract spec** with `prompts/01_extract_spec.md`.
   Output draft `spec.yaml` with `schema_version: "1.2"`. This is the semantic and layout contract: source canvas, UI style, background style, background occlusion, reusable `components[]`, layout `instances[]`, surface policy, occlusion reconstruction, resolution policy, atlas policy, layering, and render patterns.

2. **Verify spec** with `prompts/02_verify_spec.md`.
   Output corrected `spec.yaml`. This step is mandatory because VLMs may avoid overlapping bboxes, over-merge near-duplicate components, miss companion fill sprites, or fail to reconstruct partially occluded components.

3. **Generate background plate** with `prompts/02_generate_background_plate.md`.
   Output `background_plate.png`. This step is mandatory. Preserve visible background regions and infer UI-occluded regions by inpainting or generation. The final background plate must match the source canvas dimensions, but the image API generation size may be a larger standard size selected at runtime. Use `scripts/openai_image.py --size auto --purpose background --spec ui-sprite-runs/YYYY-MM-DD-slug/spec.yaml --normalize-background-to-source` when the provider supports standard sizes better than the exact source size. Do not create a stable background report YAML or image size plan YAML.

4. **Generate labeled atlas sheets** with `prompts/03_generate_ui_atlas.md`.
   First generate the formal Markdown prompt artifact with `scripts/build_atlas_prompt.py --spec ui-sprite-runs/YYYY-MM-DD-slug/spec.yaml --output ui-sprite-runs/YYYY-MM-DD-slug/atlas/buttons_01.prompt.md --component-group buttons --atlas-bg chroma-key --atlas-key-color #00ff00 --layout-strategy maxrects`. Do not handwrite the prompt, do not summarize the canonical prompt, and do not replace it with a shorter natural-language prompt. The prompt selects reusable `components[]`, includes their source instances as bbox references, and embeds MaxRects placement guidance by default so the model does not invent the atlas packing plan. MaxRects reserves label rectangles above content rectangles; labels must stay in label rectangles and sprite art must stay in content rectangles. Use `--layout-strategy area-budget` only as a legacy fallback. Then pass that Markdown file to the selected image generation service from the Generation Capability Gate. Output one or more labeled atlas PNGs under `atlas/`. The default background is `chroma-key`.
   `scripts/plan_atlas_layout.py` remains available as a standalone inspection helper. It emits stdout JSON placement guidance, but this output is not a stable contract and must not be promoted into a saved plan artifact.

5. **Verify labeled atlas sheets** with `prompts/04_verify_ui_atlas.md`.
   Check each generated atlas sheet before mapping using `effect.png`, the matching `atlas/<name>.prompt.md`, and the generated `atlas/<name>.png`. If QA reports missing components, wrong center semantics, decoration missing, unwanted texture noise, flat fill pollution, occlusion contamination, a label inside the sprite crop, fake transparency, missing alpha, or flat bar fill, rebuild a focused `atlas/<name>.prompt.md` with `scripts/build_atlas_prompt.py --component-id <id>` or `--component-group <group>` and regenerate the failed subset.

6. **Extract per-atlas crop maps** with `prompts/04_extract_atlas_map.md`.
   For each generated atlas image, read the matching `atlas/<name>.prompt.md` and output one sibling `atlas/<name>.map.yaml`. This is a per-atlas crop contract: atlas file, sprite crop bboxes, and output filenames. External id labels must not be included in crop bboxes. Do not output a global `atlas_map.yaml` in the new workflow.

7. **Slice sprites** with `scripts/ui_slice.py`.
   The slicer is mechanical: it validates inputs, crops bboxes, optionally removes border-connected background, and writes `sprites/*.png`. It does not infer, confirm, correct, generate reports, or draw debug overlays.

8. **Build render manifest** with `scripts/build_render_manifest.py`.
   Output `render.yaml`. This compact HTML input joins instance layout from `spec.yaml` with sprite filenames from `atlas/*.map.yaml`. spec.yaml is authoritative: `instances[]` are authoritative for source bbox, display size, z-index, render-param overrides, and layer intent; `components[]` are authoritative for render pattern and sprite identity.

9. **Generate Playwright HTML** with `prompts/05_generate_playwright_html.md`.
   Output `index.html` from `render.yaml`. Use static Jinja-style HTML/CSS with `background_plate.png` behind absolutely positioned sprites. The page serves Playwright screenshots only. JavaScript is limited to `window.__UI_READY__ = true` and optional `?debug=1` overlay. If static rendering fails, ask before injecting temporary JS patches. Capture the Playwright verification screenshot as `final.png`.

## Stable Contracts

Keep two stable YAML-first contract files. `spec.yaml` is strict `schema_version: "1.2"`; old `spec.yaml` files where `components[]` also carried layout are not accepted. Existing `atlas_map.yaml` or `.json` run files remain readable as legacy input for helper scripts, but the new workflow does not create a global atlas map.

| File | Purpose |
| --- | --- |
| `spec.yaml` | Semantic UI, background, reusable component definitions, layout instances, resolution, atlas, and rendering intent |
| `render.yaml` | Compact HTML input with spec-sourced layout and atlas-sourced sprite filenames |

`components[]` defines sprite art once. `instances[]` places that art in the source scene. Merge only exactly identical component definitions; do not merge near-duplicates, mirrored or rotated variants, state variants, different lighting or shadow direction, unique attached decorations, or anything uncertain.

`atlas/*.map.yaml` files are scoped per-atlas crop contracts for VLM accuracy. They are not a global stable contract and must be merged only in script memory while slicing or building `render.yaml`. Do not promote `atlas_map.yaml` into the new workflow. Do not promote `sheet_plan.yaml`, `background_report.yaml`, `slice_report.yaml`, `render_report.yaml`, or any generated image-size plan into stable contracts. Runtime image size and atlas packing decisions belong in helper arguments, generated prompts, and stdout, not in another stable artifact.

## Labeled Atlas Default

Default Phase 4 uses `scripts/build_atlas_prompt.py` to generate an observable labeled atlas prompt. The generated image uses `--atlas-bg chroma-key --atlas-key-color #00ff00` by default. Chroma-key is a removable key-color background for image models that do not support true alpha; final sprite transparency comes from `scripts/ui_slice.py --bg-policy transparentize-border --bg-color #00ff00`, not from the image service. Use `--atlas-bg solid-key` only for legacy gray-key output or manual inspection. Use `--atlas-bg transparent` only when explicitly requested and when the provider reliably supports true alpha. Component ids are external labels used for map extraction. Labels must remain inside their MaxRects label rectangles and outside sprite crop bboxes.

Each `atlas/<name>.prompt.md` contains a Local Atlas Spec JSON block with `schema_version`, `source_image`, `style`, `atlas_context`, selected `components[]`, and selected `instances[]`. Phase 4 VLM steps use this local atlas contract, not the full `spec.yaml`, to avoid token bloat and cross-atlas component confusion. The full `spec.yaml` is read again in Phase 8 by `scripts/build_render_manifest.py`.

Transparent atlas output must contain true RGBA alpha with 0% alpha background pixels. Checkerboard, grid, transparent preview patterns, gray-white squares, RGB output, or any visual simulation of transparency are failed transparent output. Do not silently fall back; ask for chroma-key regeneration or a provider that supports real alpha.

`debug_bbox.png`, when produced by a slicer or downstream debug tool, is only a visualization of an existing coordinate map for human review. It is not the source of automatic sprite recognition.

Treat scripts as stable command-line helpers during normal execution. Prefer SKILL.md examples and `--help`; read script source only when changing the helper, debugging unexpected behavior, or validating security-sensitive behavior.

If `build_atlas_prompt.py` rejects a spec because it describes source-derived atlas art, fix the spec and rerun Phase 2. Do not bypass the helper, do not create a local atlas-packing script, and do not continue to slicing or HTML from locally cropped art.

## Slicer

```bash
python scripts/ui_slice.py \
  --atlas-dir ui-sprite-runs/YYYY-MM-DD-slug/atlas \
  --out ui-sprite-runs/YYYY-MM-DD-slug/sprites \
  --bg-policy keep
```

Default chroma-key background cleanup:

```bash
python scripts/ui_slice.py \
  --atlas-dir ui-sprite-runs/YYYY-MM-DD-slug/atlas \
  --out ui-sprite-runs/YYYY-MM-DD-slug/sprites \
  --bg-policy transparentize-border \
  --bg-color #00ff00 \
  --bg-tolerance 18
```

Optional white or gray background cleanup:

```bash
python scripts/ui_slice.py \
  --atlas-dir ui-sprite-runs/YYYY-MM-DD-slug/atlas \
  --out ui-sprite-runs/YYYY-MM-DD-slug/sprites \
  --bg-policy transparentize-border \
  --bg-color auto \
  --bg-tolerance 18
```

`transparentize-border` removes only pixels connected to the crop border and near the detected background color. It must not delete all matching white pixels globally, because white may be part of the item material.

## External Image Generation Fallback

### Generation Capability Gate

Run this gate before Phase 2 or Phase 3. Check native image-generation tools first: if the current runtime exposes an image generation tool such as Codex Desktop `image_gen`, an `imagegen` skill/tool, or another MCP/tool entry that can create or edit raster images, use that native tool for background plates and labeled atlas sheets. Do not ask for external image API configuration when a native generative tool is available and sufficient for the current image task.

Only generative image services count: an available native image generation tool, a configured OpenAI-compatible endpoint, or an external generation/edit service explicitly confirmed by the user. Do not check local image-processing tools as substitutes. Pillow/OpenCV/canvas/crop are reference preparation only; they may prepare masks, prompts, contact sheets, or debug overlays, but they do not satisfy the generation requirement.

Use this priority order:

1. Native runtime image generation tool, including Codex Desktop `image_gen` or an equivalent built-in imagegen capability.
2. Already configured workspace or run `.env` for `scripts/openai_image.py`.
3. External image API fallback setup.

scripts/openai_image.py is the fallback only when no native generative tool is available or when the user explicitly chooses an OpenAI-compatible endpoint for this run.

If no generative service is available, stop and configure the external image API. Create `ui-sprite-runs/.gitignore` and `ui-sprite-runs/.env` first if they do not exist, then ask the user to edit the created `ui-sprite-runs/.env`. Do not continue into spec-to-atlas production, deterministic slicing, or HTML reconstruction while waiting for generation credentials.

Use external image API configuration only when no native generative tool is available for the mandatory background plate or UI atlas steps. Phase 2 and Phase 3 are mandatory generation steps; local image processing may prepare masks, prompts, or validation, but it must not replace image generation.

Do not take a token-saving shortcut. "Usable result", "fast delivery", "no built-in image tool", or "preserve original style" is not a reason to replace generation with deterministic component slicing. Absolute-positioned HTML reconstruction from crops is an invalid substitute for this workflow: it produces dirty rectangular cutouts, mixed background pixels, clipped decoration, and fixed ugly corners on complex UI deco.

Ask the user before calling any external service. Before continuing, request the image API base URL, model or endpoint shape, and API key delivery method. Explain that the token and uploaded effect image will be exposed to the tool execution environment and the configured image service. Recommend a temporary, low-scope, revocable API key.

Create a shared `ui-sprite-runs/.env` from `config/image-api.env.example` and prompt the user to edit that file. A run-local `.env` may override it only for a single invocation. The .env file is the preferred environment variable source for `scripts/openai_image.py`. This avoids pasting API keys into prompts and avoids visible shell commands with tokens. Do not paste API keys into prompts, generated scripts, command arguments, logs, schemas, screenshots, or HTML. Do not commit `.env` files.

Use `scripts/openai_image.py` for OpenAI-compatible image generation or edit endpoints. The script reads `IMAGE_API_BASE_URL`, `IMAGE_API_KEY`, `IMAGE_API_MODEL`, `IMAGE_API_SIZE`, `IMAGE_API_QUALITY`, `IMAGE_API_RESPONSE_FORMAT`, and `IMAGE_API_TIMEOUT` from the environment, explicit `--env-file`, or `--run-dir` env lookup. With `--run-dir ui-sprite-runs/YYYY-MM-DD-slug`, it reads `ui-sprite-runs/.env` first and then `ui-sprite-runs/YYYY-MM-DD-slug/.env` for overrides. It also accepts non-secret `--base-url` overrides, but it does not accept an API key argument. It handles JSON `/images/generations`, multipart `/images/edits`, repeated `--input-image` fields, timeout, HTTP response status errors, JSON response parsing, `b64_json` output, image URL output, output file creation, runtime `--size auto` selection, and optional background cover-crop normalization. `--purpose background` uses `spec.source_image.width/height` to choose the nearest standard generation size and can normalize the final image back to the source canvas. `--purpose atlas` treats size as a high-resolution sheet preference and does not force the source canvas aspect ratio onto atlas art.

Example:

```bash
mkdir -p ui-sprite-runs/YYYY-MM-DD-slug
cp .agents/skills/ui-sprite-generator/templates/runs.gitignore ui-sprite-runs/.gitignore
cp .agents/skills/ui-sprite-generator/config/image-api.env.example ui-sprite-runs/.env
python .agents/skills/ui-sprite-generator/scripts/openai_image.py \
  --run-dir ui-sprite-runs/YYYY-MM-DD-slug \
  --spec ui-sprite-runs/YYYY-MM-DD-slug/spec.yaml \
  --purpose background \
  --size auto \
  --normalize-background-to-source \
  --prompt-file ui-sprite-runs/YYYY-MM-DD-slug/background_plate.prompt.txt \
  --mode edits \
  --input-image ui-sprite-runs/YYYY-MM-DD-slug/effect.png \
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
| Letting the slicer fix coordinates | Fix the relevant `atlas/*.map.yaml` or legacy `atlas_map.json`; the slicer should fail on bad bboxes |
| Debugging atlas crops in the slicer | Use final HTML `?debug=1` overlay for render/debug inspection |
| Replacing Phase 2 or Phase 3 with local segmentation | Stop and call `scripts/openai_image.py`, or ask the user to finish `ui-sprite-runs/.env` configuration |
| Shipping deterministic component slicing as a "usable result" | Treat it as invalid; crops are analysis reference only, not formal atlas art |
| Creating a custom run script that packs `source.crop(...)` results into `atlas/*.png` | Delete that run output and regenerate atlas art through a real image generation service |
| Handwriting a short atlas prompt | Use `scripts/build_atlas_prompt.py` to generate a focused `atlas/<name>.prompt.md` |
| Mapping multiple atlas sheets at once | Run `prompts/04_extract_atlas_map.md` once per atlas image |

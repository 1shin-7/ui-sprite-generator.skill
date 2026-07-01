# ui-sprite-generator.skill

<p align="center">
  <img src="https://socialify.git.ci/1shin-7/ui-sprite-generator.skill/image?description=1&font=Inter&forks=1&issues=1&language=1&name=1&owner=1&pattern=Signal&pulls=1&stargazers=1&theme=Auto" alt="ui-sprite-generator social preview" />
</p>

<p align="center">
  <a href="https://github.com/1shin-7/ui-sprite-generator.skill">
    <img alt="GitHub repo" src="https://img.shields.io/badge/GitHub-ui--sprite--generator.skill-181717?style=for-the-badge&logo=github" />
  </a>
  <img alt="Skill" src="https://img.shields.io/badge/Codex-Skill-10A37F?style=for-the-badge&logo=openai&logoColor=white" />
  <img alt="Docs language" src="https://img.shields.io/badge/Docs-CN%20%7C%20EN-2563EB?style=for-the-badge" />
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
</p>

<p align="center">
  <a href="./README.md">English</a> |
  <a href="./README.zh-CN.md">简体中文</a>
</p>

> Convert game UI mockups into clean background plates, per-atlas crop maps, sliced sprites, and Playwright-ready static HTML.

`ui-sprite-generator.skill` is a Codex skill for turning a game UI mockup into a Playwright-capturable static reconstruction: clean background plate, regenerated labeled UI atlas sheets, sliced sprite PNGs, and HTML.

## Features

- Reconstructs UI mockups as semantic assets instead of rectangular screenshot crops.
- Generates a strict `spec.yaml` v1.2 contract with reusable component definitions and lightweight layout instances.
- Restores `background_plate.png` by removing foreground UI and regenerating occluded background regions.
- Uses labeled atlas sheets by default so agents and humans can verify component identity before slicing.
- Keeps each atlas image next to its own `*.map.yaml`, so VLM crop extraction only sees one image at a time.
- Keeps atlas slicing mechanical through `scripts/ui_slice.py`; no hidden coordinate correction in the slicer.
- Supports OpenAI-compatible `/images/generations` and `/images/edits` endpoints through `scripts/openai_image.py`.
- Produces static Playwright-oriented HTML with `window.__UI_READY__ = true` and optional debug overlay.

## Quickstart

Install the skill into a workspace:

```bash
pnpx skills add https://github.com/1shin-7/ui-sprite-generator.skill --skill ui-sprite-generator
```

## Concept

The workflow is intentionally split into contracts and mechanical steps:

1. `spec.yaml` describes what the mockup means.
2. `background_plate.png` restores the world behind the UI.
3. `components[]` defines each reusable sprite once; `instances[]` places it in the source scene.
4. Labeled atlas sheets regenerate clean UI components with visible external ids.
5. `atlas/*.map.yaml` records crop coordinates for one atlas image at a time.
6. `render.yaml` combines instance layout with per-atlas sprite filenames.
7. `ui_slice.py` slices sprites without inventing or correcting art.
8. `index.html` reconstructs the scene for Playwright screenshots.

The default is labeled atlas sheets, not an unlabeled formal atlas. Labels make failures observable: missing decorations, polluted flat fills, occlusion contamination, label overlap, overgenerated detail, and non-rectangular bar fills can be caught before final slicing.

Repeated UI elements are deduplicated only when they are exactly identical and interchangeable. Near-duplicates stay separate.

## Dev

Run focused tests:

```bash
python -B -m unittest tests.test_build_spritesheet_prompt
python -B -m unittest tests.test_openai_image_script
python -B -m unittest tests.test_ui_slice
python -B -m unittest tests.test_build_render_manifest
```

Run the full local suite:

```bash
python -B -m unittest tests.test_skill_docs tests.test_build_spritesheet_prompt tests.test_build_atlas_prompt tests.test_openai_image_script tests.test_ui_slice tests.test_package_layout tests.test_data_io tests.test_build_render_manifest
python -m py_compile ui-sprite-generator/scripts/openai_image.py ui-sprite-generator/scripts/build_atlas_prompt.py ui-sprite-generator/scripts/build_spritesheet_prompt.py ui-sprite-generator/scripts/ui_slice.py ui-sprite-generator/scripts/data_io.py ui-sprite-generator/scripts/atlas_maps.py ui-sprite-generator/scripts/build_render_manifest.py
git diff --check
```

Repository layout:

```text
ui-sprite-generator/
  SKILL.md
  prompts/
  schemas/
  scripts/
  templates/
tests/
```

Do not commit `ui-sprite-runs/`, `.env`, generated screenshots, or local reference experiments.

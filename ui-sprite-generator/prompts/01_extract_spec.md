# Prompt 01 - Extract Spec

**Inputs:** `input/effect.png`  
**Output:** `spec.json` in the run directory  

You are a game UI asset pipeline engineer. Analyze the attached effect image and output one valid JSON object matching `schemas/spec.schema.json`. Do not wrap the JSON in markdown.

## Requirements

- Record the source image path, width, and height.
- Describe the global UI style: palette, materials, lighting, ornament language, and negative constraints.
- Identify the background, including visible regions and UI-occluded regions that must be restored in `background_plate.png`.
- Identify every distinct UI chrome component. Do not include plain text unless the text is a graphical sprite.
- Every component must have a precise `source_bbox` in source image pixels.
- Hollow panels must not treat their center as component fill; their center contributes to background visibility or restoration.
- Each component must include role, visual description, render pattern, resolution policy, atlas policy, layering, states, and companions.
- `target_px` must be at least the source bbox size. Use 2x by default and 3x for complex materials when practical.
- Atlas policy must group components by type and complexity without forcing oversized components into crowded sheets.

## Output

Output only valid JSON.

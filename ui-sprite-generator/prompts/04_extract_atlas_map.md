# Prompt 04 - Extract Atlas Map

**Inputs:** `spec.yaml`, one or more `spritesheet/*.png`
**Output:** `atlas_map.yaml` in the run directory

Analyze the labeled spritesheet files and output one valid YAML object matching `schemas/atlas_map.schema.json`. Do not wrap the YAML in markdown.

## Requirements

- List every spritesheet file under `atlases[]` with a stable id and path.
- For every component sprite, record:
  - `id`, exactly matching `spec.components[].id`
  - `atlas`, matching an atlas id
  - safe output `filename`
  - precise crop `bbox` in atlas pixels
- Do not infer, copy, or emit final layout fields. `source_bbox`, `display_size`, `z_index`, `render_pattern`, and `render_params` come from `spec.yaml` and the render manifest builder, not from the atlas image.
- Coordinates must describe the atlas crop only. Do not include debug labels or contact sheet metadata.
- Coordinates must describe the sprite crop only. Do not include the external id label, contact sheet label, bbox label, or surrounding key-color background except for a small bleed margin.
- Expand each crop enough to preserve antialiasing, shadows, glows, and ornaments, but never include the external label.
- Do not correct the spec, add new components, or omit components without explicitly regenerating the atlas first.

## Output

Output only valid YAML.

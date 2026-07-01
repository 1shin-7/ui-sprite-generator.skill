# Prompt 04 - Extract Atlas Map

**Inputs:** `atlas/<name>.prompt.md`, one generated atlas image such as `atlas/buttons_01.png`
**Output:** sibling per-atlas map such as `atlas/buttons_01.map.yaml`

Analyze exactly one labeled atlas image and output only one per-atlas YAML object matching `schemas/per_atlas_map.schema.json`. Do not wrap the YAML in markdown. Do not output a global atlas_map.yaml.

Use the Local Atlas Spec JSON inside `atlas/<name>.prompt.md` as the local atlas contract. Do not request or read the full `spec.yaml` for this map extraction step; only components selected into this atlas are relevant.

## Requirements

- Set `atlas.id` to the atlas file stem and `atlas.file` to the sibling PNG filename.
- For every component sprite, record:
  - `id`, exactly matching one selected component id from `atlas/<name>.prompt.md`
  - safe output `filename`
  - precise crop `bbox` in atlas pixels
- Do not infer, copy, or emit final layout fields. `source_bbox`, `display_size`, `z_index`, `render_pattern`, and `render_params` come from the full `spec.yaml` later in Phase 8 and the render manifest builder, not from the atlas image.
- Coordinates must describe the atlas crop only. Do not include debug labels or contact sheet metadata.
- Coordinates must describe the sprite crop only. Do not include the external id label, contact sheet label, bbox label, or surrounding key-color background except for a small bleed margin.
- Expand each crop enough to preserve antialiasing, shadows, glows, and ornaments, but never include the external label.
- Do not correct the spec, add new components, or omit components without explicitly regenerating the atlas first.

## Output

Output only valid YAML.

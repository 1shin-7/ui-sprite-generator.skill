# Prompt 02 - Verify And Complete Spec

**Inputs:** same conversation as `prompts/01_extract_spec.md`, `input/effect.png`, draft `spec.yaml`
**Output:** corrected `spec.yaml` in the run directory

Review the draft `spec.yaml` against the attached effect image. Perform these passes, then output the corrected final YAML only.

## Pass 1 - Completeness

Scan the effect image top-to-bottom and left-to-right. For every visible UI chrome region, confirm which component id covers it. If a region is missing, add it.

## Pass 2 - Type Adequacy

For each component:

- Check whether its role fully captures the rendering behavior.
- If none of the known roles fits, use `custom_{descriptive_name}` and keep a valid render pattern.
- If it has a dynamic or rich fill, split it into a companion fill sprite such as `bar_fill_texture`.
- If it tiles or repeats, set the render pattern to `tiled_repeat`.
- If it has visible states, create one component entry per state.
- If it is structurally composite, split it into smaller sprites.

## Pass 3 - Geometry, Surface, And Occlusion

- `source_bbox` values may overlap. Do not shift, shrink, or offset bboxes to avoid overlaps.
- Each bbox must cover the actual visual bounds of its component, including shadows, glows, protruding ornaments, and anti-aliased edges.
- For clean solid-color UI, set `surface_policy` to `flat_fill`; do not describe random texture.
- For textured material, set `surface_policy` to `textured_fill`.
- For hollow or transparent regions, set `surface_policy` to `hollow` or `transparent`.
- If a component is covered by text, another UI element, badge, popover, or floating effect, mark `occlusion.status` as `partially_occluded` and describe how the spritesheet should redraw the complete unobstructed sprite.

Output only valid YAML.

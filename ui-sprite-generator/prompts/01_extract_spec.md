# Prompt 01 - Extract Spec

**Inputs:** `input/effect.png`  
**Output:** `spec.yaml` in the run directory

You are a game UI asset pipeline engineer. Analyze the attached effect image and output one valid YAML object matching `schemas/spec.schema.json`. Do not wrap the YAML in markdown.

## Requirements

- Record the source image path, width, and height.
- Describe the global UI style: `ui_style`, `background_style`, palette, materials, lighting, ornament language, and negative constraints. Spritesheet generation uses `ui_style`; background plate generation uses `background_style`.
- Extract a complete specification for regenerating UI components as isolated sprites, not for cropping them from the source image.
- Identify the background, including visible regions and UI-occluded regions that must be restored in `background_plate.png`.
- Identify every distinct UI chrome component. Do not include plain text unless the text is a graphical sprite.
- Every component must have a precise `source_bbox` in source image pixels.
- `source_bbox` values may overlap. Source_bbox values may overlap by design. Do not shift, shrink, or offset a bbox just to avoid overlap with another component, text, badge, floating overlay, or neighboring UI.
- Hollow panels must not treat their center as component fill; their center contributes to background visibility or restoration.
- Each component must include role, visual description, attached decorations, center type, `surface_policy`, `occlusion`, tiling, render pattern, resolution policy, atlas policy, layering, states, and companions.
- `target_px` must be at least the source bbox size. Use 2x by default and 3x only for complex materials when practical.
- Small icons, badges, and clean flat UI components should stay max 2x unless the source itself contains readable detail that would be lost. Do not upscale low-detail source art so far that generation invents detail.
- Never solve packing by increasing target_px. If a group is too large for one sheet, split it into smaller sheets.
- Atlas policy must group components by type and complexity without forcing oversized components into crowded sheets.

## Component Analysis Rules

- Cover every distinct UI chrome element visible in the mockup.
- Describe each component visually in isolation: border decoration, frame material, trim, bevel, glow, texture, ornaments, and transparent or hollow regions.
- Do not simplify ornate border decoration into plain rectangles.
- If a component has physically attached decorations, list every attached decoration.
- If a component is structurally composite, split it into smaller sprites rather than describing a single rectangular crop.
- If a progress bar has rich interior texture, glow, or pattern, split it into a hollow `bar_track` component and a `bar_fill_texture` companion rendered as a rectangular full-width fill texture behind the track or frame. Do not infer an irregular visible silhouette from decorative occlusion; HTML clipping/masking handles the visible shape.
- If a component tiles or repeats, mark its tiling direction and use `tiled_repeat`.
- If a component has distinct visual states, create one entry per state.
- If a component surface is a clean solid color, set `surface_policy` to `flat_fill` so the spritesheet prompt preserves clean flat color and avoids random texture.
- If a component is partially covered by text, badges, popovers, glows, floating decorations, neighboring UI, or another component, set `occlusion.status` to `partially_occluded` and describe how to reconstruct the complete unobstructed sprite.
- Use negative constraints to prevent generator drift.

## Discovery Rules

- Known roles are examples, not a closed set. Use `custom_{descriptive_name}` when none fits.
- For every `custom_*` role, choose a render pattern from `background_image`, `nine_slice`, `linear_clip`, `radial_clip`, `tiled_repeat`, or `overlay_stack`, and write enough visual detail for HTML reconstruction.
- For progress bars with rich interior texture, split the bar into a hollow `bar_track` and a full-width `bar_fill_texture` companion.

## Output

Output only valid YAML.

# Prompt 04 - Verify UI Atlas

**Inputs:** `effect.png`, `atlas/<name>.prompt.md`, one generated `atlas/<name>.png`
**Output:** valid JSON correction report or `{"status":"approved"}`

You are a QA engineer for a game UI sprite pipeline. Compare the original effect image, the Local Atlas Spec JSON inside `atlas/<name>.prompt.md`, and the generated labeled UI atlas.

Use the `.prompt.md` file as the local atlas contract for this image. Do not request or read the full `spec.yaml` for this verification step; the prompt file already contains the selected components, selected instances, source image metadata, UI style, and atlas background mode needed for this atlas.

For each selected component, evaluate:

```json
{
  "status": "approved | needs_revision",
  "components": [
    {
      "id": "<component id>",
      "present": true,
      "center_correct": true,
      "decoration_missing": false,
      "unwanted_texture_noise": false,
      "flat_fill_pollution": false,
      "overgenerated_detail": false,
      "occlusion_contamination": false,
      "label_inside_sprite": false,
      "source_background_pixels": false,
      "clipped_ornament": false,
      "fake_transparency": false,
      "missing_alpha": false,
      "flat_bar_fill": false,
      "non_rectangular_bar_fill": false,
      "issues": "",
      "fix_instruction": ""
    }
  ]
}
```

## Evaluation Rules

- `present`: the component is visible and identifiable.
- `center_correct`: `hollow` and `transparent` centers remain empty or transparent; `filled` regions use the intended material.
- `decoration_missing`: declared `attached_decorations` are absent or oversimplified.
- `unwanted_texture_noise`: a clean UI surface contains random lines, grit, painterly texture, mottled noise, or unrelated marks.
- `flat_fill_pollution`: a `flat_fill` component is no longer clean and flat.
- `overgenerated_detail`: a flat, low-detail, icon-like, or small source component has invented internal line art, symbols, texture, cracks, or ornament detail not present in the source UI style.
- `occlusion_contamination`: an occluded component still contains the text, badge, overlay, neighboring UI, or copied source pixels that covered it in the mockup.
- `label_inside_sprite`: an id label touches or overlaps the sprite crop area.
- `source_background_pixels`: source background, neighboring UI, copied text, or icon fragments appear around a sprite edge.
- `clipped_ornament`: ornaments, glow, bevels, shadows, or protruding silhouettes are cut off by a rectangle.
- `fake_transparency`: transparent mode produced checkerboard, grid, transparent preview pattern, gray-white squares, or any visual simulation of alpha.
- `missing_alpha`: transparent mode produced RGB output or non-transparent background pixels instead of true 0% alpha.
- `flat_bar_fill`: a `bar_fill_texture` component is flat color instead of rich texture, glow, or pattern.
- `non_rectangular_bar_fill`: a `bar_fill_texture` component has collapsed inward, rounded itself, followed ornate frame occlusion, or otherwise became a non-rectangular fill texture.

If any component has an issue, set `status` to `needs_revision` and provide exact regeneration instructions. The next generation must use `scripts/build_atlas_prompt.py --component-id <id>` or `--component-group <group>` for the failed subset.

If `fake_transparency` or `missing_alpha` is true for a transparent atlas request, treat the transparent atlas as failed. Do not silently fall back to solid-key output; ask for default solid-key regeneration or a provider that supports real alpha.

Output only valid JSON.

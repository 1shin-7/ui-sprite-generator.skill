# Prompt 04 - Verify Labeled Spritesheet

**Inputs:** `input/effect.png`, `spec.yaml`, one generated `spritesheet/*.png`
**Output:** valid JSON correction report or `{"status":"approved"}`  

You are a QA engineer for a game UI sprite pipeline. Compare the original effect image, the selected component contract in `spec.yaml`, and the generated labeled spritesheet.

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
- `flat_bar_fill`: a `bar_fill_texture` component is flat color instead of rich texture, glow, or pattern.
- `non_rectangular_bar_fill`: a `bar_fill_texture` component has collapsed inward, rounded itself, followed ornate frame occlusion, or otherwise became a non-rectangular fill texture.

If any component has an issue, set `status` to `needs_revision` and provide exact regeneration instructions. The next generation should use `scripts/build_spritesheet_prompt.py --component-id <id>` or `--component-group <group>` for the failed subset.

Output only valid JSON.

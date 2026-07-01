# Prompt 04 - Verify UI Atlas

**Inputs:** `input/effect.png`, `spec.yaml`, one generated `atlas/*.png`
**Output:** valid JSON correction report or `{"status":"approved"}`

You are a QA engineer for a game UI sprite pipeline. Compare the original effect image, the selected component contract in `spec.yaml`, and the generated UI atlas.

For each selected component, evaluate:

```json
{
  "status": "approved | needs_revision",
  "components": [
    {
      "id": "<component id>",
      "present": true,
      "center_correct": true,
      "invented_internal_texture": false,
      "decoration_missing": false,
      "source_background_pixels": false,
      "clipped_ornament": false,
      "flat_bar_fill": false,
      "issues": "",
      "fix_instruction": ""
    }
  ]
}
```

## Evaluation Rules

- `present`: the component is visible and identifiable.
- `center_correct`: `hollow` and `transparent` centers remain empty or transparent; `filled` regions use the intended material.
- `invented_internal_texture`: true when an empty center contains invented illustration, material, decorative texture, or unrelated interior content.
- `decoration_missing`: true when declared `attached_decorations` are absent or oversimplified.
- `source_background_pixels`: true when source background, neighboring UI, copied text, or icon fragments appear around a sprite edge.
- `clipped_ornament`: true when ornaments, glow, bevels, shadows, or protruding silhouettes are cut off by a rectangle.
- `flat_bar_fill`: true when a `bar_fill_texture` component is flat color instead of a rich texture, glow, or pattern.

If any component has an issue, set `status` to `needs_revision` and provide exact regeneration instructions. The next generation should use `scripts/build_atlas_prompt.py --component-id <id>` or `--component-group <group>` for the failed subset.

Output only valid JSON.

# Prompt 03 - Generate UI Atlases

**Inputs:** `input/effect.png`, `spec.json`  
**Outputs:** one or more `atlas/*.png` files in the run directory  

Generate game-ready UI sprite atlas images from the components in `spec.json`.

## Atlas Rules

- Use transparent backgrounds for formal atlas files.
- Do not draw id labels, bbox labels, or cell labels into formal atlas files.
- You may produce separate debug/contact sheets for human viewing, but Phase 3 must use only formal atlas files.
- Prefer `1536x1024` or `1024x1536` when suitable, but custom canvas sizes and orientations are allowed.
- Do not reduce sprite resolution to fit a canvas.
- Preserve at least the source component resolution. Use the component's `resolution_policy.target_px`.
- Keep comfortable gutters: use each component's `atlas_policy.minimum_gutter`.
- Do not rotate components.
- Large panels, nine-slice frames, complex ornaments, resource orbs, and detailed bars may be isolated or grouped sparsely.
- Small related components may share sheets by group: slots, buttons, tabs, badges, bars, ornaments.

## Output Naming

Use descriptive atlas filenames such as:

```text
atlas/atlas_panels_01.png
atlas/atlas_slots_01.png
atlas/atlas_buttons_01.png
atlas/atlas_bars_01.png
```

All visible UI components from `spec.components[]` must appear in exactly one formal atlas unless the component intentionally uses companions or states.

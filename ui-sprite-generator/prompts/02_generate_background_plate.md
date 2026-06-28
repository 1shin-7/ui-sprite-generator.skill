# Prompt 02 - Generate Background Plate

**Inputs:** `input/effect.png`, `spec.json`  
**Output:** `background_plate.png` in the run directory  

Create a complete background plate for the full source canvas.

## Requirements

- The output image dimensions must exactly match `spec.source_image.width` and `spec.source_image.height`.
- Preserve visible background regions from the effect image wherever possible.
- Restore UI-occluded regions using inpainting or generation guided by `spec.background.occluded_regions`.
- Do not include UI chrome components, text, icons, slots, bars, panels, buttons, or other foreground UI sprites.
- The result should work as the bottom layer in a static Playwright screenshot reconstruction.

## Output

Save only `background_plate.png`. Do not create a stable JSON report.

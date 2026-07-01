# Prompt 02 - Generate Background Plate

**Inputs:** `input/effect.png`, `spec.yaml`
**Output:** `background_plate.png` in the run directory  

Create a complete background plate for the full source canvas.

## Requirements

- The final `background_plate.png` dimensions must exactly match `spec.source_image.width` and `spec.source_image.height`; final background_plate.png is the normalized Playwright bottom-layer asset.
- The API generation size may be a larger standard size selected at runtime. Preserve the source aspect intent so the generated result can be cleanly cover-cropped and resized into the final background plate.
- Preserve visible background regions from the effect image wherever possible.
- Restore UI-occluded regions using inpainting or generation guided by `spec.background.occluded_regions`.
- Do not include UI chrome components, text, icons, slots, bars, panels, buttons, or other foreground UI sprites.
- Do not use the whole effect image as the background plate.
- Do not preserve foreground UI chrome and plan to cover it later with sprites.
- Remove foreground UI first, then inpaint or regenerate every occluded background region so the plate is a clean bottom layer.
- Cropped source rectangles, deterministic masks, or local fills may be used only as references for the generation request; they are not the output.
- If no available tool can remove UI and infer the hidden background, stop and ask for an image-generation service instead of creating a fake background plate.
- The result should work as the bottom layer in a static Playwright screenshot reconstruction.

## Output

Save only `background_plate.png`. Do not create a stable JSON report.

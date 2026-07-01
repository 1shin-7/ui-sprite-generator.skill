# Prompt 05 - Generate Playwright HTML

**Inputs:** `render.yaml`, `background_plate.png`, `sprites/*.png`
**Output:** `index.html` in the run directory

Generate a static HTML page for Playwright screenshot capture only.

## Rendering Contract

- `.ui-root` must have fixed pixel dimensions matching `render.root_size`.
- Place `background_plate.png` as the bottom layer, covering the full root.
- Render each sprite instance with absolute positioning from `render` coordinates, using its `id`, `component`, `w`, `h`, `z_index`, and `render_pattern`.
- Use relative asset paths from run-root `index.html`.
- Do not use frameworks, bundlers, hydration, interaction, hover behavior, or runtime rendering APIs.
- JavaScript is limited to:
  - `window.__UI_READY__ = true`
  - optional `?debug=1` overlay showing final sprite boxes and ids
- If static CSS cannot express a layout correction, ask before adding a temporary JS patch.

## Pattern Notes

- `background_image`: one absolutely positioned div with `background-size: 100% 100%`.
- `linear_clip`: track sprite plus clipped fill wrapper. The fill image remains full size; the wrapper clips progress.
- `radial_clip`: use CSS mask or static layering as described by `render_params`.
- `nine_slice`: use CSS `border-image` with offsets from `render_params`.
- `tiled_repeat`: use repeat direction and tile size from `render_params`.
- `overlay_stack`: render companion sprites in a relative wrapper using declared z order.

## Output

Output a single `index.html`.

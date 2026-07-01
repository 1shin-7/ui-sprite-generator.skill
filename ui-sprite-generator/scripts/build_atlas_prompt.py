#!/usr/bin/env python3
"""Build the canonical Markdown prompt for UI atlas image generation."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from data_io import DataIOError, load_data  # noqa: E402


class PromptBuildError(Exception):
    pass


CANONICAL_PROMPT = """# UI Atlas Generation Prompt

You are a game UI sprite sheet artist. Generate game-ready UI sprite atlas images from the selected spec components.

## Visual Reference

The attached effect image is the source style reference. Match its material, color tone, border thickness, trim, ornament vocabulary, bevels, glow, transparency, and texture detail. Use the selected component contract below for structure and component identity. If the component contract and image conflict on visual style, the image wins.

## Redraw Contract

- Do not rewrite this prompt into a shorter prompt.
- Do not summarize, omit, compress, or reinterpret the rules below.
- Do not crop rectangular regions from the source effect image and call them sprites.
- Do not use Pillow, canvas crop, screenshot crop, or any non-generative fallback to create atlas art.
- Do not take a token-saving shortcut such as deterministic slicing, "cut reusable UI blocks", or absolute-positioned HTML reconstruction from crops.
- Each atlas entry must be a newly redrawn isolated sprite that preserves the source UI style.
- Complex UI is not rectangular cutting: border decoration, corner ornaments, bevels, drop shadows, glows, transparent holes, and rich material texture must be reconstructed around the component's actual shape.
- The source `source_bbox` is only a size and placement reference. It is not permission to cut that rectangle out of the effect image.
- If an available tool cannot redraw isolated sprites, stop and ask for an image-generation service instead of silently falling back to crop-based output.

## Atlas Rules

- Use transparent backgrounds for formal atlas files unless this prompt was built in contact-sheet mode.
- Do not draw id labels, bbox labels, or cell labels into formal atlas files.
- A formal sprite must follow the actual silhouette of the UI element, including protruding ornaments, soft glow, bevel shadow, and transparent cutouts. A dirty rectangular cutout is failed output.
- If source background pixels visible around a sprite edge, clipped ornament, copied text/icon fragments, neighboring UI fragments, or hard rectangular corners appear in the atlas, regenerate the sprite.
- Do not reduce sprite resolution to fit a canvas.
- Preserve at least the source component resolution. Use each component's `resolution_policy.target_px`.
- Keep comfortable gutters. Use each component's `atlas_policy.minimum_gutter`.
- Do not rotate components.
- Large panels, nine-slice frames, complex ornaments, resource orbs, and detailed bars may be isolated or grouped sparsely.
- Small related components may share sheets by group: slots, buttons, tabs, badges, bars, ornaments.
- Split into multiple atlas sheets when needed. Do not prioritize away required components just to fit one canvas.
- Each isolated sprite must include all attached border decoration and ornaments declared in the component contract.
- Hollow or transparent centers must remain empty: no interior content, no illustrative fill, no material fill, and no decorative texture unless the component data explicitly specifies that center content exists.
- Style words affect only allowed component surfaces: border, trim, bevel, ornament, glow, material, and declared filled regions.
- A `hollow` component must have transparent or empty center pixels, not a filled rectangle copied from the effect image.
- A `transparent` component must keep transparent areas transparent.
- A `filled` component may use the source fill material and texture described in the spec.
- A `bar_fill_texture` component must be a full-width 100% fill texture with rich texture, glow, or pattern; a flat color is not acceptable.
- A `bar_track` component must remain hollow where the fill will be clipped in HTML.
- A `nine_slice` component must keep fixed corners in corner regions and produce stretchable edges/center.
- A `tiled_repeat` component must be designed as a seamless tile.

## Output Naming

Use descriptive atlas filenames such as:

```text
atlas/atlas_panels_01.png
atlas/atlas_slots_01.png
atlas/atlas_buttons_01.png
atlas/atlas_bars_01.png
```
"""


def load_spec(path):
    try:
        return load_data(path)
    except DataIOError as exc:
        raise PromptBuildError(str(exc)) from exc


def require_spec_v12(spec):
    if spec.get("schema_version") != "1.2":
        raise PromptBuildError("spec.schema_version must be 1.2")


def select_components(spec, component_group=None, component_ids=None):
    require_spec_v12(spec)
    components = list(spec.get("components", []))
    if component_group:
        components = [
            component
            for component in components
            if component.get("atlas_policy", {}).get("group") == component_group
        ]
    if component_ids:
        wanted = set(component_ids)
        components = [component for component in components if component.get("id") in wanted]
    if not components:
        raise PromptBuildError("no components selected for atlas prompt")
    return components


def source_instances_by_component(spec):
    grouped = {}
    for instance in spec.get("instances", []):
        if instance.get("rendered") is False:
            continue
        component_id = instance.get("uses")
        if not component_id:
            continue
        grouped.setdefault(component_id, []).append(instance)
    return grouped


def format_bbox(bbox):
    return f"x={bbox['x']}, y={bbox['y']}, w={bbox['w']}, h={bbox['h']}"


def format_target_px(component):
    target = component["resolution_policy"]["target_px"]
    return f"{target['w']}x{target['h']}"


def format_instance(instance):
    return f"{instance['id']} ({format_bbox(instance['source_bbox'])})"


def component_contract_markdown(components, source_instances):
    lines = [
        "## Selected Component Contract",
        "",
        "The following component contract is authoritative. Use it mechanically; do not replace it with a shorter natural-language summary.",
        "",
    ]
    for index, component in enumerate(components, start=1):
        lines.extend(
            [
                f"### {index}. `{component['id']}`",
                "",
                f"- role: {component['role']}",
                f"- source_instances: {'; '.join(format_instance(item) for item in source_instances.get(component['id'], [])) or 'none'}",
                f"- visual_description: {component['visual_description']}",
                f"- attached_decorations: {', '.join(component['attached_decorations']) or 'none'}",
                f"- center: {component['center']}",
                f"- render_pattern: {component['render_pattern']}",
                f"- target_px: {format_target_px(component)}",
                f"- minimum_source_scale: {component['resolution_policy']['minimum_source_scale']}",
                f"- recommended_generation_scale: {component['resolution_policy']['recommended_generation_scale']}",
                f"- allow_downscale: {component['resolution_policy']['allow_downscale']}",
                f"- atlas_group: {component['atlas_policy']['group']}",
                f"- minimum_gutter: {component['atlas_policy']['minimum_gutter']}",
                f"- states: {', '.join(component['states']) or 'default'}",
                f"- companions: {', '.join(component['companions']) or 'none'}",
                "",
            ]
        )
    return "\n".join(lines)


def raw_json_markdown(style, components, source_instances):
    data = {
        "style": style,
        "components": components,
        "source_instances": {
            component["id"]: [
                {"id": instance["id"], "source_bbox": instance["source_bbox"]}
                for instance in source_instances.get(component["id"], [])
            ]
            for component in components
        },
    }
    return "\n".join(
        [
            "## Raw Selected Spec JSON",
            "",
            "```json",
            dump_data_to_string(data),
            "```",
            "",
        ]
    )


def dump_data_to_string(data):
    import json

    return json.dumps(data, ensure_ascii=False, indent=2)


def build_prompt(
    spec,
    atlas_mode="transparent",
    component_group=None,
    component_ids=None,
    canvas_size="1536x1024",
    include_raw_json=True,
):
    components = select_components(spec, component_group=component_group, component_ids=component_ids)
    source_instances = source_instances_by_component(spec)
    sections = [
        CANONICAL_PROMPT.rstrip(),
        "",
        "## Build Parameters",
        "",
        f"- atlas_mode: {atlas_mode}",
        f"- canvas_size: {canvas_size}",
        "- canvas_size is a generation canvas preference, not permission to downscale sprites.",
        "",
        component_contract_markdown(components, source_instances),
    ]
    if include_raw_json:
        sections.append(raw_json_markdown(spec["style"], components, source_instances))
    return "\n".join(sections).rstrip() + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build the canonical Markdown prompt for UI atlas generation.")
    parser.add_argument("--spec", required=True, type=Path, help="Path to spec.yaml or spec.json")
    parser.add_argument("--output", required=True, type=Path, help="Output Markdown prompt path")
    parser.add_argument("--atlas-mode", choices=["transparent", "contact-sheet"], default="transparent")
    parser.add_argument("--component-group", help="Only include components with this atlas_policy.group")
    parser.add_argument("--component-id", action="append", help="Only include this component id; repeat as needed")
    parser.add_argument("--canvas-size", default="1536x1024", help="Preferred generation canvas size")
    parser.add_argument("--include-raw-json", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        spec = load_spec(args.spec)
        prompt = build_prompt(
            spec,
            atlas_mode=args.atlas_mode,
            component_group=args.component_group,
            component_ids=args.component_id,
            canvas_size=args.canvas_size,
            include_raw_json=args.include_raw_json,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(prompt, encoding="utf-8")
        print(f"Saved atlas prompt: {args.output}")
    except PromptBuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

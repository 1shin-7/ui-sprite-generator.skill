#!/usr/bin/env python3
"""Build the canonical Markdown prompt for labeled UI spritesheet generation."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from data_io import DataIOError, load_data  # noqa: E402


class PromptBuildError(Exception):
    pass


CANONICAL_PROMPT = """# UI Spritesheet Generation Prompt

You are a game UI sprite sheet artist. Generate a clean, observable UI spritesheet from the selected spec components.

## Visual Reference

The attached effect image is the SOURCE MOCKUP. Match its UI material, color tone, border thickness, trim, ornament vocabulary, bevels, glow, transparency, and texture detail. Use only the UI style from the selected component contract below. Do not copy background scenery, characters, text, or unrelated screenshot content into sprite surfaces.

## Redraw Contract

- Do not crop rectangular regions from the source effect image and call them sprites.
- Each spritesheet entry must be a newly redrawn isolated UI sprite that preserves the source UI style.
- Do not use Pillow, canvas crop, screenshot crop, or deterministic slicing to create the spritesheet art.
- Do not rewrite this prompt into a shorter prompt.
- Do not summarize, omit, compress, or reinterpret the rules below.

## Spritesheet Rules

- Arrange selected components in a loose grid with comfortable gutters.
- Print each component id in small neutral gray text outside and above its sprite.
- The external label must not overlap, touch, or be inside the sprite crop area.
- Do not draw text, numbers, bbox labels, or ids inside any sprite.
- Hollow or transparent centers must remain empty: no interior content, no illustrative fill, no material fill, and no decorative texture unless the component data explicitly says that center content exists.
- Style words affect only allowed component surfaces: border, trim, bevel, ornament, glow, material, and declared filled regions.
- A `flat_fill` component must stay clean and flat. Do not add painterly texture, random lines, grit, noise, brush strokes, invented symbols, or mottled shading.
- Do not invent detail. If the source UI is flat, low-detail, or icon-like, preserve that simplicity instead of adding extra line art, grain, symbols, cracks, brushwork, or internal texture.
- A `textured_fill` component may use the source material texture described in the UI style.
- A `bar_fill_texture` component must be a full-width 100% fill texture with rich texture, glow, or pattern; a flat color is not acceptable.
- A `bar_fill_texture` component is a full rectangular fill texture behind its track or frame. Do not infer a non-rectangular silhouette from decorative frame occlusion; clipping and masking happen later in HTML.
- For `occlusion.status = partially_occluded`, redraw a complete unobstructed sprite. Do not include the text, badge, floating overlay, neighboring sprite, or source pixels that cover it in the mockup.
- Preserve all declared attached decorations and protruding silhouettes.
- Keep enough bleed around antialiasing, shadows, glows, and ornaments.
- Do not rotate components.
- Split into multiple spritesheets when needed. Do not prioritize fitting one canvas over clarity or target resolution.
- Do not increase target_px to solve packing; split the request into smaller sheets instead.

## Output Naming

Save the generated image as a labeled atlas file such as:

```text
atlas/buttons_01.png
atlas/panels_01.png
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


def parse_size(size):
    try:
        width_text, height_text = size.lower().split("x", 1)
        width = int(width_text)
        height = int(height_text)
    except (AttributeError, ValueError) as exc:
        raise PromptBuildError(f"invalid canvas size: {size}") from exc
    if width <= 0 or height <= 0:
        raise PromptBuildError(f"invalid canvas size: {size}")
    return width, height


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
        raise PromptBuildError("no components selected for spritesheet prompt")
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


def target_px(component):
    target = component["resolution_policy"]["target_px"]
    return int(target["w"]), int(target["h"])


def target_area(components):
    return sum(width * height for width, height in (target_px(component) for component in components))


def fill_budget(components, canvas_size, max_fill_ratio):
    canvas_width, canvas_height = parse_size(canvas_size)
    area = target_area(components)
    limit = canvas_width * canvas_height * max_fill_ratio
    return area, int(limit), area > limit


def max_generation_scale(component):
    role = component.get("role", "").lower()
    surface_policy = component.get("surface_policy", "").lower()
    if role == "bar_fill_texture" or surface_policy == "flat_fill":
        return 2
    if "icon" in role or "badge" in role:
        return 2
    return 3


def packing_guidance(selected_area, fill_limit, over_budget):
    lines = [
        "## Packing Guidance",
        "",
        f"- selected_target_area: {selected_area}",
        f"- fill_budget_area: {fill_limit}",
    ]
    if over_budget:
        lines.extend(
            [
                "- Selected components exceed the fill budget for this canvas.",
                "- Action: split this request into smaller sheets by `atlas_group` or explicit `--component-id` subsets.",
                "- Do not increase target_px, scale, or sprite resolution to make packing look better.",
            ]
        )
    else:
        lines.append("- Selected components fit within the fill budget.")
    lines.append("")
    return "\n".join(lines)


def style_contract(spec):
    style = spec.get("style", {})
    return {
        "description": style.get("description", ""),
        "ui_style": style.get("ui_style", style.get("description", "")),
        "palette": style.get("palette", []),
        "materials": style.get("materials", []),
        "lighting": style.get("lighting", ""),
        "ornament_language": style.get("ornament_language", ""),
        "negative_constraints": style.get("negative_constraints", []),
    }


def format_bbox(bbox):
    return f"x={bbox['x']}, y={bbox['y']}, w={bbox['w']}, h={bbox['h']}"


def format_target(component):
    width, height = target_px(component)
    return f"{width}x{height}"


def background_contract(sheet_mode):
    if sheet_mode == "transparent":
        return "- Use a transparent RGBA canvas. Keep sprites separated and preserve alpha."
    return "- Use a solid `#e0e0e0` canvas background. The key color is outside sprites and may be removed by the slicer."


def format_instance(instance):
    return f"{instance['id']} ({format_bbox(instance['source_bbox'])})"


def component_contract_markdown(components, source_instances):
    lines = [
        "## Selected Component Contract",
        "",
        "Use this contract mechanically. The id label is external; the sprite itself must contain only UI chrome.",
        "",
    ]
    for index, component in enumerate(components, start=1):
        occlusion = component.get("occlusion", {})
        lines.extend(
            [
                f"### {index}. `{component['id']}`",
                "",
                f"- role: {component['role']}",
                f"- source_instances: {'; '.join(format_instance(item) for item in source_instances.get(component['id'], [])) or 'none'}",
                f"- visual_description: {component['visual_description']}",
                f"- attached_decorations: {', '.join(component['attached_decorations']) or 'none'}",
                f"- center: {component['center']}",
                f"- surface_policy: {component.get('surface_policy', component['center'])}",
                f"- occlusion_status: {occlusion.get('status', 'unoccluded')}",
                f"- occlusion_reconstruction: {occlusion.get('reconstruction', 'redraw as visible')}",
                f"- render_pattern: {component['render_pattern']}",
                f"- target_px: {format_target(component)}",
                f"- max_generation_scale: {max_generation_scale(component)}x",
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
    sheet_mode="solid-key",
    component_group=None,
    component_ids=None,
    canvas_size="1536x1024",
    max_fill_ratio=0.65,
    include_raw_json=True,
):
    components = select_components(spec, component_group=component_group, component_ids=component_ids)
    source_instances = source_instances_by_component(spec)
    selected_area, fill_limit, over_budget = fill_budget(components, canvas_size, max_fill_ratio)
    style = style_contract(spec)
    sections = [
        CANONICAL_PROMPT.rstrip(),
        "",
        "## Build Parameters",
        "",
        f"- sheet_mode: {sheet_mode}",
        f"- canvas_size: {canvas_size}",
        f"- max_fill_ratio: {max_fill_ratio}",
        "- canvas size is a generation preference, not the source image dimensions.",
        background_contract(sheet_mode),
        "",
        packing_guidance(selected_area, fill_limit, over_budget),
        component_contract_markdown(components, source_instances),
    ]
    if include_raw_json:
        sections.append(raw_json_markdown(style, components, source_instances))
    return "\n".join(sections).rstrip() + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build the canonical Markdown prompt for UI spritesheet generation.")
    parser.add_argument("--spec", required=True, type=Path, help="Path to spec.yaml or spec.json")
    parser.add_argument("--output", required=True, type=Path, help="Output Markdown prompt path")
    parser.add_argument("--sheet-mode", choices=["solid-key", "transparent"], default="solid-key")
    parser.add_argument("--component-group", help="Only include components with this atlas_policy.group")
    parser.add_argument("--component-id", action="append", help="Only include this component id; repeat as needed")
    parser.add_argument("--canvas-size", default="1536x1024", help="Preferred generation canvas size")
    parser.add_argument("--max-fill-ratio", type=float, default=0.65, help="Maximum selected target area / canvas area")
    parser.add_argument("--include-raw-json", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.max_fill_ratio <= 0:
            raise PromptBuildError("--max-fill-ratio must be > 0")
        spec = load_spec(args.spec)
        prompt = build_prompt(
            spec,
            sheet_mode=args.sheet_mode,
            component_group=args.component_group,
            component_ids=args.component_id,
            canvas_size=args.canvas_size,
            max_fill_ratio=args.max_fill_ratio,
            include_raw_json=args.include_raw_json,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(prompt, encoding="utf-8")
        print(f"Saved spritesheet prompt: {args.output}")
    except PromptBuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the canonical Markdown prompt for labeled UI atlas generation."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from data_io import DataIOError, load_data  # noqa: E402
from plan_atlas_layout import (  # noqa: E402
    LayoutError,
    SpriteItem,
    layout_to_data,
    pack_groups_maxrects,
)


class PromptBuildError(Exception):
    pass


CANONICAL_PROMPT = """# UI Atlas Generation Prompt

You are a game UI sprite artist. Generate a clean, observable labeled atlas sheet from the selected spec components.

## Visual Reference

The attached effect image is the SOURCE MOCKUP. Match its UI material, color tone, border thickness, trim, ornament vocabulary, bevels, glow, transparency, and texture detail. Use only the UI style from the selected component contract below. Do not copy background scenery, characters, text, or unrelated screenshot content into sprite surfaces.

## Redraw Contract

- Do not crop rectangular regions from the source effect image and call them sprites.
- Each labeled atlas entry must be a newly redrawn isolated UI sprite that preserves the source UI style.
- Do not use Pillow, canvas crop, screenshot crop, or deterministic slicing to create the atlas art.
- Do not rewrite this prompt into a shorter prompt.
- Do not summarize, omit, compress, or reinterpret the rules below.

## Atlas Rules

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
- Split into multiple labeled atlas sheets when needed. Do not prioritize fitting one canvas over clarity or target resolution.
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


SOURCE_DERIVED_ART_PATTERNS = [
    "source pixels",
    "source pixel",
    "extracted directly",
    "directly extracted",
    "cropped from",
    "crop from",
    "screenshot crop",
    "deterministic slicing",
    "local split",
    "copied from the source",
]


def text_values(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(text_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(text_values(item))
        return values
    return []


def validate_generation_contract(components):
    for component in components:
        component_id = component.get("id", "<unknown>")
        contract_text = "\n".join(
            text_values(
                {
                    "visual_description": component.get("visual_description", ""),
                    "occlusion": component.get("occlusion", {}),
                    "states": component.get("states", []),
                }
            )
        ).lower()
        for pattern in SOURCE_DERIVED_ART_PATTERNS:
            if pattern in contract_text:
                raise PromptBuildError(
                    f"{component_id}: component contract describes source-derived atlas art ({pattern})"
                )
        for state in component.get("states", []):
            if isinstance(state, str) and state.lower() in {"source", "cropped", "extracted"}:
                raise PromptBuildError(f"{component_id}: component state must describe a UI state, not {state!r}")


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
        raise PromptBuildError("no components selected for atlas prompt")
    validate_generation_contract(components)
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
                "- Action: split this request into smaller atlas sheets by `atlas_group` or explicit `--component-id` subsets.",
                "- Do not increase target_px, scale, or sprite resolution to make packing look better.",
            ]
        )
    else:
        lines.append("- Selected components fit within the fill budget.")
    lines.append("")
    return "\n".join(lines)


def sprite_items_from_components(components):
    items = []
    for component in components:
        width, height = target_px(component)
        items.append(SpriteItem(component["id"], width, height, component.get("atlas_policy", {}).get("group")))
    return items


def maxrects_layout(components, canvas_size, padding, scale, oversize):
    try:
        atlas_size = parse_size(canvas_size)
        groups = pack_groups_maxrects(
            sprite_items_from_components(components),
            atlas_size,
            padding=padding,
            scale=scale,
            oversize=oversize,
        )
    except LayoutError as exc:
        raise PromptBuildError(str(exc)) from exc
    return layout_to_data(groups, atlas_size, padding=padding, scale=scale, oversize=oversize)


def maxrects_layout_guidance(layout):
    clamped = [
        placement
        for atlas in layout["atlases"]
        for placement in atlas["placements"]
        if placement["clamped"]
    ]
    lines = [
        "## MaxRects Layout Guidance",
        "",
        "- layout_strategy: maxrects",
        f"- atlas_size: {layout['atlas_size'][0]}x{layout['atlas_size'][1]}",
        f"- atlas_count: {len(layout['atlases'])}",
        f"- padding: {layout['padding']}",
        f"- requested_scale: {layout['requested_scale']}",
        f"- oversize: {layout['oversize']}",
    ]
    if clamped:
        lines.append(f"- MaxRects clamped {len(clamped)} oversized sprite(s) to fit the selected atlas canvas.")
    lines.extend(
        [
            "- Follow these placements instead of inventing a new packing plan.",
            "- Keep labels outside each planned cell and keep sprite art inside the content rectangle.",
            "",
        ]
    )
    for atlas in layout["atlases"]:
        lines.append(f"### Atlas {atlas['index']}")
        lines.append("")
        for placement in atlas["placements"]:
            lines.append(
                "- "
                f"{placement['id']}: atlas_index={placement['atlas_index']}, "
                f"cell=(x={placement['x']}, y={placement['y']}, w={placement['w']}, h={placement['h']}), "
                f"content=(x={placement['content_x']}, y={placement['content_y']}, "
                f"content_w={placement['content_w']}, content_h={placement['content_h']}), "
                f"target_px={placement['target_w']}x{placement['target_h']}, "
                f"effective_scale={placement['effective_scale']}, clamped={str(placement['clamped']).lower()}"
            )
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


def background_contract(atlas_bg):
    if atlas_bg == "transparent":
        return (
            "- Use a true transparent RGBA canvas. Background pixels must have 0% alpha. "
            "Do not draw checkerboard, grid, transparent preview pattern, gray-white squares, "
            "or any fake transparency texture."
        )
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


def selected_instances(spec, components):
    component_ids = {component["id"] for component in components}
    return [
        instance
        for instance in spec.get("instances", [])
        if instance.get("rendered") is not False and instance.get("uses") in component_ids
    ]


def local_atlas_spec_markdown(spec, style, components, instances, atlas_context):
    data = {
        "schema_version": spec["schema_version"],
        "source_image": spec["source_image"],
        "style": style,
        "atlas_context": atlas_context,
        "components": components,
        "instances": instances,
    }
    return "\n".join(
        [
            "## Local Atlas Spec JSON",
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
    atlas_bg="solid-key",
    component_group=None,
    component_ids=None,
    canvas_size="1536x1024",
    max_fill_ratio=0.65,
    layout_strategy="maxrects",
    layout_padding=24,
    layout_scale=1.0,
    oversize="clamp",
    include_raw_json=True,
):
    components = select_components(spec, component_group=component_group, component_ids=component_ids)
    source_instances = source_instances_by_component(spec)
    selected_area, fill_limit, over_budget = fill_budget(components, canvas_size, max_fill_ratio)
    style = style_contract(spec)
    instances = selected_instances(spec, components)
    layout = None
    if layout_strategy == "maxrects":
        layout = maxrects_layout(components, canvas_size, layout_padding, layout_scale, oversize)
    elif layout_strategy != "area-budget":
        raise PromptBuildError("layout_strategy must be 'maxrects' or 'area-budget'")
    atlas_context = {
        "atlas_bg": atlas_bg,
        "canvas_size": canvas_size,
        "max_fill_ratio": max_fill_ratio,
        "selected_target_area": selected_area,
        "fill_budget_area": fill_limit,
        "over_budget": over_budget,
        "layout_strategy": layout_strategy,
    }
    if layout is not None:
        atlas_context["layout"] = layout
    sections = [
        CANONICAL_PROMPT.rstrip(),
        "",
        "## Build Parameters",
        "",
        f"- atlas_bg: {atlas_bg}",
        f"- canvas_size: {canvas_size}",
        f"- max_fill_ratio: {max_fill_ratio}",
        f"- layout_strategy: {layout_strategy}",
        "- canvas size is a generation preference, not the source image dimensions.",
        background_contract(atlas_bg),
        "",
        maxrects_layout_guidance(layout) if layout is not None else packing_guidance(selected_area, fill_limit, over_budget),
        component_contract_markdown(components, source_instances),
    ]
    if include_raw_json:
        sections.append(local_atlas_spec_markdown(spec, style, components, instances, atlas_context))
    return "\n".join(sections).rstrip() + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build the canonical Markdown prompt for UI atlas generation.")
    parser.add_argument("--spec", required=True, type=Path, help="Path to spec.yaml or spec.json")
    parser.add_argument("--output", required=True, type=Path, help="Output Markdown prompt path")
    parser.add_argument("--atlas-bg", choices=["solid-key", "transparent"], default="solid-key")
    parser.add_argument("--component-group", help="Only include components with this atlas_policy.group")
    parser.add_argument("--component-id", action="append", help="Only include this component id; repeat as needed")
    parser.add_argument("--canvas-size", default="1536x1024", help="Preferred generation canvas size")
    parser.add_argument("--max-fill-ratio", type=float, default=0.65, help="Maximum selected target area / canvas area")
    parser.add_argument("--layout-strategy", choices=["maxrects", "area-budget"], default="maxrects")
    parser.add_argument("--layout-padding", type=int, default=24, help="MaxRects cell padding around each sprite")
    parser.add_argument("--layout-scale", type=float, default=1.0, help="MaxRects target_px scale before packing")
    parser.add_argument("--oversize", choices=["clamp", "fail"], default="clamp")
    parser.add_argument("--include-raw-json", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.max_fill_ratio <= 0:
            raise PromptBuildError("--max-fill-ratio must be > 0")
        if args.layout_padding < 0:
            raise PromptBuildError("--layout-padding must be >= 0")
        if args.layout_scale <= 0:
            raise PromptBuildError("--layout-scale must be > 0")
        spec = load_spec(args.spec)
        prompt = build_prompt(
            spec,
            atlas_bg=args.atlas_bg,
            component_group=args.component_group,
            component_ids=args.component_id,
            canvas_size=args.canvas_size,
            max_fill_ratio=args.max_fill_ratio,
            layout_strategy=args.layout_strategy,
            layout_padding=args.layout_padding,
            layout_scale=args.layout_scale,
            oversize=args.oversize,
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

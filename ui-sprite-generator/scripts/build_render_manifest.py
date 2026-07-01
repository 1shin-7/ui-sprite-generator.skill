#!/usr/bin/env python3
"""Build a compact HTML render manifest from spec and atlas crop map data."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from data_io import DataIOError, dump_data, load_data  # noqa: E402
from atlas_maps import AtlasMapError, assets_by_id, load_legacy_atlas_map, load_per_atlas_maps  # noqa: E402


class RenderManifestError(Exception):
    pass


def size_from_bbox(bbox):
    return {"w": int(bbox["w"]), "h": int(bbox["h"])}


def sprite_file(filename, sprites_dir):
    if not sprites_dir:
        return filename
    return f"{str(sprites_dir).replace(chr(92), '/')}/{filename}"


def require_spec_v12(spec):
    if spec.get("schema_version") != "1.2":
        raise RenderManifestError("spec.schema_version must be 1.2")


def components_by_id(spec):
    components = {}
    for component in spec.get("components", []):
        component_id = component.get("id")
        if not component_id:
            raise RenderManifestError("component missing id")
        if component_id in components:
            raise RenderManifestError(f"duplicate component id: {component_id}")
        components[component_id] = component
    return components


def rendered_instances(spec):
    return [instance for instance in spec.get("instances", []) if instance.get("rendered") is not False]


def rendered_component_ids(spec):
    return {instance.get("uses") for instance in rendered_instances(spec) if instance.get("uses")}


def build_render_manifest(spec, atlas_assets, background="background_plate.png", sprites_dir="sprites"):
    require_spec_v12(spec)
    source = spec.get("source_image", {})
    try:
        root_size = {"w": int(source["width"]), "h": int(source["height"])}
    except (KeyError, TypeError, ValueError) as exc:
        raise RenderManifestError("spec.source_image.width and height are required") from exc

    components = components_by_id(spec)
    try:
        assets = assets_by_id(atlas_assets.get("sprites", []))
    except AtlasMapError as exc:
        raise RenderManifestError(str(exc)) from exc
    extra_ids = sorted(set(assets) - set(components))
    if extra_ids:
        raise RenderManifestError(f"sprite asset not present in spec: {extra_ids[0]}")

    for instance in rendered_instances(spec):
        instance_id = instance.get("id")
        component_id = instance.get("uses")
        if component_id not in components:
            raise RenderManifestError(f"{instance_id}: unknown component: {component_id}")

    used_component_ids = rendered_component_ids(spec)
    render_sprites = []
    for component_id in used_component_ids:
        asset = assets.get(component_id)
        if not asset:
            raise RenderManifestError(f"missing sprite asset for component: {component_id}")

    for instance in rendered_instances(spec):
        instance_id = instance.get("id")
        component_id = instance.get("uses")
        component = components.get(component_id)
        if not component:
            raise RenderManifestError(f"{instance_id}: unknown component: {component_id}")
        asset = assets.get(component_id)
        try:
            bbox = instance.get("source_bbox", {})
            layering = instance.get("layering", {})
            display_size = instance.get("display_size") or size_from_bbox(bbox)
            render_params = dict(component.get("render_params", {}))
            render_params.update(instance.get("render_params_override", {}))
            node = {
                "id": instance_id,
                "component": component_id,
                "file": sprite_file(asset["filename"], sprites_dir),
                "x": int(bbox["x"]),
                "y": int(bbox["y"]),
                "w": int(display_size["w"]),
                "h": int(display_size["h"]),
                "z_index": int(layering["z_index"]),
                "render_pattern": component["render_pattern"],
                "render_params": render_params,
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise RenderManifestError(f"{instance_id}: invalid render fields") from exc
        companions = component.get("companions", [])
        if companions:
            node["companions"] = companions
        render_sprites.append(node)

    return {
        "schema_version": "1.0",
        "root_size": root_size,
        "background": {"file": background},
        "sprites": render_sprites,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build render.yaml for Playwright HTML generation.")
    parser.add_argument("--spec", required=True, type=Path, help="Path to spec.yaml or spec.json")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--atlas-dir", type=Path, help="Directory containing atlas images and matching *.map.yaml files")
    source.add_argument("--atlas-map", type=Path, help="Legacy path to atlas_map.yaml or atlas_map.json")
    parser.add_argument("--output", required=True, type=Path, help="Output render.yaml or render.json")
    parser.add_argument("--background", default="background_plate.png", help="Background plate path from HTML dir")
    parser.add_argument("--sprites-dir", default="sprites", help="Sprite path prefix from HTML dir")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        spec = load_data(args.spec)
        if args.atlas_dir:
            atlas_assets = load_per_atlas_maps(args.atlas_dir)
        else:
            atlas_assets = load_legacy_atlas_map(args.atlas_map)
        manifest = build_render_manifest(
            spec,
            atlas_assets,
            background=args.background,
            sprites_dir=args.sprites_dir,
        )
        dump_data(manifest, args.output)
        print(f"Saved render manifest: {args.output}")
    except (DataIOError, AtlasMapError, RenderManifestError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

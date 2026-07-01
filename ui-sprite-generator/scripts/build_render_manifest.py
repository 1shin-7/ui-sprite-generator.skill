#!/usr/bin/env python3
"""Build a compact HTML render manifest from spec and atlas map data."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from data_io import DataIOError, dump_data, load_data


class RenderManifestError(Exception):
    pass


def size_from_bbox(bbox):
    return {"w": int(bbox["w"]), "h": int(bbox["h"])}


def sprite_file(filename, sprites_dir):
    if not sprites_dir:
        return filename
    return f"{str(sprites_dir).replace(chr(92), '/')}/{filename}"


def atlas_assets_by_id(atlas_map):
    assets = {}
    for sprite in atlas_map.get("sprites", []):
        sprite_id = sprite.get("id")
        filename = sprite.get("filename")
        if not sprite_id or not filename:
            raise RenderManifestError("atlas_map sprites require id and filename")
        if sprite_id in assets:
            raise RenderManifestError(f"duplicate sprite asset id: {sprite_id}")
        assets[sprite_id] = sprite
    return assets


def build_render_manifest(spec, atlas_map, background="background_plate.png", sprites_dir="sprites"):
    source = spec.get("source_image", {})
    try:
        root_size = {"w": int(source["width"]), "h": int(source["height"])}
    except (KeyError, TypeError, ValueError) as exc:
        raise RenderManifestError("spec.source_image.width and height are required") from exc

    assets = atlas_assets_by_id(atlas_map)
    render_sprites = []
    for component in spec.get("components", []):
        component_id = component.get("id")
        if component.get("rendered") is False:
            continue
        asset = assets.get(component_id)
        if not asset:
            raise RenderManifestError(f"missing sprite asset for component: {component_id}")
        try:
            bbox = component.get("source_bbox", {})
            layering = component.get("layering", {})
            display_size = component.get("display_size") or size_from_bbox(bbox)
            node = {
                "id": component_id,
                "file": sprite_file(asset["filename"], sprites_dir),
                "x": int(bbox["x"]),
                "y": int(bbox["y"]),
                "w": int(display_size["w"]),
                "h": int(display_size["h"]),
                "z_index": int(layering["z_index"]),
                "render_pattern": component["render_pattern"],
                "render_params": component.get("render_params", {}),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise RenderManifestError(f"{component_id}: invalid render fields") from exc
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
    parser.add_argument("--atlas-map", required=True, type=Path, help="Path to atlas_map.yaml or atlas_map.json")
    parser.add_argument("--output", required=True, type=Path, help="Output render.yaml or render.json")
    parser.add_argument("--background", default="background_plate.png", help="Background plate path from HTML dir")
    parser.add_argument("--sprites-dir", default="sprites", help="Sprite path prefix from HTML dir")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        spec = load_data(args.spec)
        atlas_map = load_data(args.atlas_map)
        manifest = build_render_manifest(
            spec,
            atlas_map,
            background=args.background,
            sprites_dir=args.sprites_dir,
        )
        dump_data(manifest, args.output)
        print(f"Saved render manifest: {args.output}")
    except (DataIOError, RenderManifestError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

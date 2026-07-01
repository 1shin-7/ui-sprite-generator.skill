#!/usr/bin/env python3
"""Slice UI sprite atlases from per-atlas maps or legacy atlas_map.yaml/json."""

import argparse
import re
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("ERROR: Pillow not installed. Run: pip install Pillow")

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from atlas_maps import AtlasMapError, load_legacy_atlas_map, load_per_atlas_maps, resolve_path  # noqa: E402


SAFE_FILENAME = re.compile(r"^[A-Za-z0-9_.-]+\.png$")


class SliceError(Exception):
    pass


def parse_hex_color(value):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise SliceError(f"invalid --bg-color: {value}")
    return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))


def color_distance_sq(a, b):
    return sum((int(a[i]) - int(b[i])) ** 2 for i in range(3))


def detect_border_color(image):
    width, height = image.size
    samples = []
    pixels = image.load()
    for x in range(width):
        samples.append(pixels[x, 0][:3])
        samples.append(pixels[x, height - 1][:3])
    for y in range(height):
        samples.append(pixels[0, y][:3])
        samples.append(pixels[width - 1, y][:3])
    channels = []
    for channel in range(3):
        values = sorted(sample[channel] for sample in samples)
        channels.append(values[len(values) // 2])
    return tuple(channels)


def transparentize_border(image, bg_color, tolerance, connectivity):
    image = image.convert("RGBA")
    width, height = image.size
    pixels = image.load()
    max_distance = tolerance * tolerance
    visited = set()
    queue = deque()

    def is_background(x, y):
        return pixels[x, y][3] > 0 and color_distance_sq(pixels[x, y], bg_color) <= max_distance

    def enqueue_if_bg(x, y):
        if (x, y) not in visited and is_background(x, y):
            visited.add((x, y))
            queue.append((x, y))

    for x in range(width):
        enqueue_if_bg(x, 0)
        enqueue_if_bg(x, height - 1)
    for y in range(height):
        enqueue_if_bg(0, y)
        enqueue_if_bg(width - 1, y)

    if connectivity == 8:
        neighbors = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    else:
        neighbors = [(0, -1), (-1, 0), (1, 0), (0, 1)]

    while queue:
        x, y = queue.popleft()
        for dx, dy in neighbors:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                enqueue_if_bg(nx, ny)

    for x, y in visited:
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)

    return image


def validate_filename(filename):
    if not SAFE_FILENAME.fullmatch(filename) or "/" in filename or "\\" in filename:
        raise SliceError(f"unsafe filename: {filename}")


def crop_sprite(image, sprite, bleed):
    bbox = sprite.get("bbox", {})
    try:
        x = int(bbox["x"]) - bleed
        y = int(bbox["y"]) - bleed
        w = int(bbox["w"]) + bleed * 2
        h = int(bbox["h"]) + bleed * 2
    except (KeyError, TypeError, ValueError) as exc:
        raise SliceError(f"{sprite.get('id', '<unknown>')}: invalid bbox") from exc

    width, height = image.size
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
        raise SliceError(
            f"{sprite.get('id', '<unknown>')}: bbox out of bounds "
            f"({x},{y},{w},{h}) for atlas {width}x{height}"
        )
    return image.crop((x, y, x + w, y + h))


def load_atlas_images(atlas_map, base_dir):
    atlases = {}
    for atlas in atlas_map.get("atlases", []):
        atlas_id = atlas.get("id")
        if not atlas_id:
            raise SliceError("atlas missing id")
        if atlas_id in atlases:
            raise SliceError(f"duplicate atlas id: {atlas_id}")
        atlas_path = resolve_path(base_dir, atlas.get("file", ""))
        if not atlas_path.exists():
            raise SliceError(f"atlas file not found: {atlas_path}")
        atlases[atlas_id] = Image.open(atlas_path).convert("RGBA")
    return atlases


def slice_atlas_map(atlas_map, base_dir, out_dir, bg_policy, bg_color_arg, bg_tolerance, bleed, overwrite, connectivity):
    out_dir.mkdir(parents=True, exist_ok=True)

    atlases = load_atlas_images(atlas_map, base_dir)

    seen_ids = set()
    seen_files = set()
    sprites = atlas_map.get("sprites", [])
    if not sprites:
        raise SliceError("atlas map has no sprites")

    for sprite in sprites:
        sprite_id = sprite.get("id")
        if not sprite_id:
            raise SliceError("sprite missing id")
        if sprite_id in seen_ids:
            raise SliceError(f"duplicate sprite id: {sprite_id}")
        seen_ids.add(sprite_id)

        atlas_id = sprite.get("atlas")
        if atlas_id not in atlases:
            raise SliceError(f"{sprite_id}: unknown atlas id: {atlas_id}")

        filename = sprite.get("filename")
        validate_filename(filename)
        if filename in seen_files:
            raise SliceError(f"duplicate output filename: {filename}")
        seen_files.add(filename)

        dest = out_dir / filename
        if dest.exists() and not overwrite:
            raise SliceError(f"output exists, use --overwrite: {dest}")

        crop = crop_sprite(atlases[atlas_id], sprite, bleed)
        if bg_policy == "transparentize-border":
            bg_color = detect_border_color(crop) if bg_color_arg == "auto" else parse_hex_color(bg_color_arg)
            crop = transparentize_border(crop, bg_color, bg_tolerance, connectivity)
        crop.save(dest, "PNG")
        print(f"OK {sprite_id} -> {dest}")


def slice_legacy_map(map_path, out_dir, bg_policy, bg_color_arg, bg_tolerance, bleed, overwrite, connectivity):
    try:
        atlas_map = load_legacy_atlas_map(map_path)
    except AtlasMapError as exc:
        raise SliceError(str(exc)) from exc
    slice_atlas_map(atlas_map, map_path.parent, out_dir, bg_policy, bg_color_arg, bg_tolerance, bleed, overwrite, connectivity)


def slice_atlas_dir(atlas_dir, out_dir, bg_policy, bg_color_arg, bg_tolerance, bleed, overwrite, connectivity):
    try:
        atlas_map = load_per_atlas_maps(atlas_dir)
    except AtlasMapError as exc:
        raise SliceError(str(exc)) from exc
    slice_atlas_map(atlas_map, atlas_dir, out_dir, bg_policy, bg_color_arg, bg_tolerance, bleed, overwrite, connectivity)


def main():
    parser = argparse.ArgumentParser(description="Slice UI sprite atlases from atlas/*.map.yaml or legacy atlas_map.yaml/json")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--atlas-dir", type=Path, help="Directory containing atlas images and matching *.map.yaml files")
    source.add_argument("--map", type=Path, help="Legacy path to atlas_map.yaml or atlas_map.json")
    parser.add_argument("--out", required=True, type=Path, help="Output directory for sliced sprites")
    parser.add_argument("--bg-policy", choices=["keep", "transparentize-border"], default="keep")
    parser.add_argument("--bg-color", default="auto", help="'auto' or #rrggbb for transparentize-border")
    parser.add_argument("--bg-tolerance", type=int, default=18, help="RGB distance tolerance per channel")
    parser.add_argument("--connectivity", type=int, choices=[4, 8], default=4)
    parser.add_argument("--bleed", type=int, default=0, help="Extra pixels around every crop; must remain in atlas bounds")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    args = parser.parse_args()

    if args.bg_tolerance < 0:
        parser.error("--bg-tolerance must be >= 0")
    if args.bleed < 0:
        parser.error("--bleed must be >= 0")

    try:
        if args.atlas_dir:
            slice_atlas_dir(
                args.atlas_dir,
                args.out,
                args.bg_policy,
                args.bg_color,
                args.bg_tolerance,
                args.bleed,
                args.overwrite,
                args.connectivity,
            )
        else:
            slice_legacy_map(
                args.map,
                args.out,
                args.bg_policy,
                args.bg_color,
                args.bg_tolerance,
                args.bleed,
                args.overwrite,
                args.connectivity,
            )
    except SliceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

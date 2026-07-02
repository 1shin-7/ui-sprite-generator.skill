#!/usr/bin/env python3
"""Plan deterministic UI atlas cell layouts with a MaxRects heuristic."""

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from data_io import DataIOError, load_data  # noqa: E402


OversizePolicy = Literal["clamp", "fail"]


class LayoutError(ValueError):
    pass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    def contains(self, other: "Rect") -> bool:
        return self.x <= other.x and self.y <= other.y and self.right >= other.right and self.bottom >= other.bottom

    def intersects(self, other: "Rect") -> bool:
        return self.x < other.right and self.right > other.x and self.y < other.bottom and self.bottom > other.y


@dataclass(frozen=True)
class SpriteItem:
    id: str
    target_w: int
    target_h: int
    group: str | None = None


@dataclass(frozen=True)
class PackedItem:
    item: SpriteItem
    order: int
    cell_w: int
    cell_h: int
    inner_w: int
    content_w: int
    content_h: int
    label_w: int
    label_h: int
    label_gap: int
    requested_scale: float
    effective_scale: float
    clamped: bool


@dataclass(frozen=True)
class Placement:
    id: str
    atlas_index: int
    x: int
    y: int
    w: int
    h: int
    label_x: int
    label_y: int
    label_w: int
    label_h: int
    label_gap: int
    content_x: int
    content_y: int
    content_w: int
    content_h: int
    target_w: int
    target_h: int
    requested_scale: float
    effective_scale: float
    clamped: bool


class MaxRectsBin:
    """Mutable single-atlas MaxRects state."""

    def __init__(self, atlas_index: int, atlas_size: tuple[int, int], padding: int) -> None:
        self.atlas_index = atlas_index
        self.padding = padding
        self.free_rects = [Rect(0, 0, atlas_size[0], atlas_size[1])]
        self.placements: list[Placement] = []

    def score(self, packed: PackedItem) -> tuple[int, int, int, int] | None:
        best_score = None
        for free_rect in self.free_rects:
            if packed.cell_w > free_rect.w or packed.cell_h > free_rect.h:
                continue
            leftover_w = free_rect.w - packed.cell_w
            leftover_h = free_rect.h - packed.cell_h
            score = (min(leftover_w, leftover_h), max(leftover_w, leftover_h), free_rect.y, free_rect.x)
            if best_score is None or score < best_score:
                best_score = score
        return best_score

    def insert(self, packed: PackedItem) -> Placement | None:
        best_rect = None
        best_score = None
        for free_rect in self.free_rects:
            if packed.cell_w > free_rect.w or packed.cell_h > free_rect.h:
                continue
            leftover_w = free_rect.w - packed.cell_w
            leftover_h = free_rect.h - packed.cell_h
            score = (min(leftover_w, leftover_h), max(leftover_w, leftover_h), free_rect.y, free_rect.x)
            if best_score is None or score < best_score:
                best_score = score
                best_rect = free_rect
        if best_rect is None:
            return None

        cell = Rect(best_rect.x, best_rect.y, packed.cell_w, packed.cell_h)
        self._split_free_rects(cell)
        placement = Placement(
            id=packed.item.id,
            atlas_index=self.atlas_index,
            x=cell.x,
            y=cell.y,
            w=cell.w,
            h=cell.h,
            label_x=cell.x + self.padding if packed.label_h else 0,
            label_y=cell.y + self.padding if packed.label_h else 0,
            label_w=packed.label_w,
            label_h=packed.label_h,
            label_gap=packed.label_gap,
            content_x=cell.x + self.padding + ((packed.inner_w - packed.content_w) // 2),
            content_y=cell.y + self.padding + packed.label_h + packed.label_gap,
            content_w=packed.content_w,
            content_h=packed.content_h,
            target_w=packed.item.target_w,
            target_h=packed.item.target_h,
            requested_scale=packed.requested_scale,
            effective_scale=packed.effective_scale,
            clamped=packed.clamped,
        )
        self.placements.append(placement)
        return placement

    def _split_free_rects(self, used: Rect) -> None:
        next_free = []
        for free_rect in self.free_rects:
            if not free_rect.intersects(used):
                next_free.append(free_rect)
                continue
            if used.x > free_rect.x:
                next_free.append(Rect(free_rect.x, free_rect.y, used.x - free_rect.x, free_rect.h))
            if used.right < free_rect.right:
                next_free.append(Rect(used.right, free_rect.y, free_rect.right - used.right, free_rect.h))
            if used.y > free_rect.y:
                next_free.append(Rect(free_rect.x, free_rect.y, free_rect.w, used.y - free_rect.y))
            if used.bottom < free_rect.bottom:
                next_free.append(Rect(free_rect.x, used.bottom, free_rect.w, free_rect.bottom - used.bottom))
        self.free_rects = self._prune_free_rects([rect for rect in next_free if rect.w > 0 and rect.h > 0])

    @staticmethod
    def _prune_free_rects(rects: list[Rect]) -> list[Rect]:
        kept = []
        for index, rect in enumerate(rects):
            if any(other_index != index and other.contains(rect) for other_index, other in enumerate(rects)):
                continue
            kept.append(rect)
        return kept


def parse_size(text: str) -> tuple[int, int]:
    """Parse `WxH` into positive integer dimensions."""
    try:
        width_text, height_text = text.lower().split("x", 1)
        width = int(width_text)
        height = int(height_text)
    except (AttributeError, ValueError) as exc:
        raise LayoutError(f"invalid size {text!r}; expected WxH") from exc
    if width <= 0 or height <= 0:
        raise LayoutError(f"invalid size {text!r}; dimensions must be > 0")
    return width, height


def estimate_label_width(text: str, char_width: int = 8) -> int:
    """Estimate external label width in atlas pixels."""
    return max(1, len(text) * char_width)


def items_from_spec(
    spec: dict,
    *,
    component_group: str | None = None,
    component_ids: Sequence[str] | None = None,
) -> list[SpriteItem]:
    """Extract atlas-plannable sprite items from a spec v1.2 object."""
    # TODO: Consider optional type/style grouping in a future planner pass so a sheet can hold only buttons,
    # icons, or another cohesive component family without asking the VLM to infer that layout split.
    if spec.get("schema_version") != "1.2":
        raise LayoutError("spec.schema_version must be 1.2")
    wanted_ids = set(component_ids or [])
    seen_ids = set()
    items = []
    for component in spec.get("components", []):
        component_id = component.get("id")
        if not component_id:
            raise LayoutError("component id is required")
        if component_id in seen_ids:
            raise LayoutError(f"duplicate component id: {component_id}")
        seen_ids.add(component_id)

        group = component.get("atlas_policy", {}).get("group")
        if component_group and group != component_group:
            continue
        if wanted_ids and component_id not in wanted_ids:
            continue
        try:
            target = component["resolution_policy"]["target_px"]
            target_w = int(target["w"])
            target_h = int(target["h"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LayoutError(f"{component_id}: resolution_policy.target_px.w/h are required") from exc
        if target_w <= 0 or target_h <= 0:
            raise LayoutError(f"{component_id}: target_px dimensions must be > 0")
        items.append(SpriteItem(component_id, target_w, target_h, group))
    if not items:
        raise LayoutError("no components selected for atlas layout")
    return items


def prepare_items(
    items: Sequence[SpriteItem],
    atlas_size: tuple[int, int],
    *,
    padding: int = 0,
    scale: float = 1.0,
    oversize: OversizePolicy = "clamp",
    label_height: int = 20,
    label_gap: int = 20,
) -> list[PackedItem]:
    """Scale and validate items before MaxRects packing."""
    validate_common_inputs(items, atlas_size, padding, scale, oversize, label_height, label_gap)
    atlas_w, atlas_h = atlas_size
    max_content_w = atlas_w - padding * 2
    max_content_h = atlas_h - padding * 2 - label_height - label_gap
    if max_content_w <= 0 or max_content_h <= 0:
        raise LayoutError("padding leaves no usable atlas area")

    packed_items = []
    for order, item in enumerate(items):
        label_w = min(estimate_label_width(item.id), max_content_w) if label_height else 0
        inner_w = max(label_w, 1)
        planned_w = math.ceil(item.target_w * scale)
        planned_h = math.ceil(item.target_h * scale)
        effective_scale = scale
        clamped = False
        if planned_w > max_content_w or planned_h > max_content_h:
            if oversize == "fail":
                raise LayoutError(
                    f"{item.id}: scaled size {planned_w}x{planned_h} plus padding {padding} exceeds atlas "
                    f"{atlas_w}x{atlas_h}"
                )
            effective_scale = min(max_content_w / item.target_w, max_content_h / item.target_h)
            planned_w = max(1, math.floor(item.target_w * effective_scale))
            planned_h = max(1, math.floor(item.target_h * effective_scale))
            clamped = True
        if planned_w <= 0 or planned_h <= 0:
            raise LayoutError(f"{item.id}: clamped content size is invalid")
        inner_w = max(inner_w, planned_w)
        cell_w = inner_w + padding * 2
        cell_h = planned_h + label_height + label_gap + padding * 2
        if cell_w > atlas_w or cell_h > atlas_h:
            raise LayoutError(f"{item.id}: packed cell {cell_w}x{cell_h} exceeds atlas {atlas_w}x{atlas_h}")
        packed_items.append(
            PackedItem(
                item=item,
                order=order,
                cell_w=cell_w,
                cell_h=cell_h,
                inner_w=inner_w,
                content_w=planned_w,
                content_h=planned_h,
                label_w=inner_w if label_height else 0,
                label_h=label_height,
                label_gap=label_gap,
                requested_scale=scale,
                effective_scale=effective_scale,
                clamped=clamped,
            )
        )
    return packed_items


def validate_common_inputs(
    items: Sequence[SpriteItem],
    atlas_size: tuple[int, int],
    padding: int,
    scale: float,
    oversize: OversizePolicy,
    label_height: int,
    label_gap: int,
) -> None:
    if not items:
        raise LayoutError("no items to pack")
    atlas_w, atlas_h = atlas_size
    if atlas_w <= 0 or atlas_h <= 0:
        raise LayoutError("atlas dimensions must be > 0")
    if padding < 0:
        raise LayoutError("padding must be >= 0")
    if label_height < 0:
        raise LayoutError("label_height must be >= 0")
    if label_gap < 0:
        raise LayoutError("label_gap must be >= 0")
    if label_height == 0 and label_gap != 0:
        raise LayoutError("label_gap must be 0 when label_height is 0")
    if scale <= 0:
        raise LayoutError("scale must be > 0")
    if oversize not in {"clamp", "fail"}:
        raise LayoutError("oversize must be 'clamp' or 'fail'")
    seen_ids = set()
    for item in items:
        if item.id in seen_ids:
            raise LayoutError(f"duplicate item id: {item.id}")
        seen_ids.add(item.id)
        if item.target_w <= 0 or item.target_h <= 0:
            raise LayoutError(f"{item.id}: target dimensions must be > 0")


def sort_packed_items(items: Sequence[PackedItem]) -> list[PackedItem]:
    return sorted(items, key=lambda item: (max(item.cell_w, item.cell_h), item.cell_w * item.cell_h), reverse=True)


def pack_maxrects(
    items: list[SpriteItem],
    atlas_size: tuple[int, int],
    *,
    padding: int = 0,
    scale: float = 1.0,
    oversize: OversizePolicy = "clamp",
    label_height: int = 20,
    label_gap: int = 20,
) -> list[Placement]:
    """Pack items into one atlas using MaxRects; raise if any item cannot fit."""
    packed_items = prepare_items(
        items,
        atlas_size,
        padding=padding,
        scale=scale,
        oversize=oversize,
        label_height=label_height,
        label_gap=label_gap,
    )
    atlas = MaxRectsBin(0, atlas_size, padding)
    for packed in sort_packed_items(packed_items):
        if atlas.insert(packed) is None:
            raise LayoutError(f"{packed.item.id}: item does not fit in one atlas")
    return sorted(atlas.placements, key=lambda placement: next(i for i, item in enumerate(items) if item.id == placement.id))


def pack_groups_maxrects(
    items: list[SpriteItem],
    atlas_size: tuple[int, int],
    *,
    padding: int = 0,
    scale: float = 1.0,
    oversize: OversizePolicy = "clamp",
    label_height: int = 20,
    label_gap: int = 20,
) -> list[list[Placement]]:
    """Pack items into as many atlases as needed using a MaxRects heuristic."""
    order_by_id = {item.id: index for index, item in enumerate(items)}
    packed_items = prepare_items(
        items,
        atlas_size,
        padding=padding,
        scale=scale,
        oversize=oversize,
        label_height=label_height,
        label_gap=label_gap,
    )
    atlases: list[MaxRectsBin] = []
    for packed in sort_packed_items(packed_items):
        best_index = None
        best_score = None
        for index, atlas in enumerate(atlases):
            score = atlas.score(packed)
            if score is not None and (best_score is None or score < best_score):
                best_index = index
                best_score = score
        if best_index is None:
            atlas = MaxRectsBin(len(atlases), atlas_size, padding)
            if atlas.insert(packed) is None:
                raise LayoutError(f"{packed.item.id}: item does not fit in an empty atlas")
            atlases.append(atlas)
        else:
            atlases[best_index].insert(packed)
    return [sorted(atlas.placements, key=lambda placement: order_by_id[placement.id]) for atlas in atlases]


def layout_to_data(
    groups: list[list[Placement]],
    atlas_size: tuple[int, int],
    *,
    padding: int,
    scale: float,
    oversize: OversizePolicy,
    label_height: int,
    label_gap: int,
) -> dict:
    return {
        "atlas_size": [atlas_size[0], atlas_size[1]],
        "padding": padding,
        "label_height": label_height,
        "label_gap": label_gap,
        "requested_scale": scale,
        "oversize": oversize,
        "atlases": [
            {
                "index": index,
                "placements": [asdict(placement) for placement in placements],
            }
            for index, placements in enumerate(groups)
        ],
    }


def load_spec(path: Path) -> dict:
    try:
        return load_data(path)
    except DataIOError as exc:
        raise LayoutError(str(exc)) from exc


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan deterministic MaxRects layouts for UI atlas generation.")
    parser.add_argument("--from-spec", required=True, type=Path, help="Path to spec.yaml or spec.json")
    parser.add_argument("--atlas", required=True, help="Atlas canvas size as WxH")
    parser.add_argument("--component-group", help="Only include components with this atlas_policy.group")
    parser.add_argument("--component-id", action="append", help="Only include this component id; repeat as needed")
    parser.add_argument("--padding", type=int, default=0, help="Pixels of empty cell padding around each sprite")
    parser.add_argument("--label-height", type=int, default=20, help="External label row height; use 0 for unlabeled")
    parser.add_argument("--label-gap", type=int, default=20, help="Gap between external label row and sprite content")
    parser.add_argument("--scale", type=float, default=1.0, help="Requested target_px scale before packing")
    parser.add_argument("--oversize", choices=["clamp", "fail"], default="clamp")
    parser.add_argument("--single", action="store_true", help="Require all selected components to fit one atlas")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        spec = load_spec(args.from_spec)
        atlas_size = parse_size(args.atlas)
        items = items_from_spec(spec, component_group=args.component_group, component_ids=args.component_id)
        if args.single:
            placements = pack_maxrects(
                items,
                atlas_size,
                padding=args.padding,
                scale=args.scale,
                oversize=args.oversize,
                label_height=args.label_height,
                label_gap=args.label_gap,
            )
            groups = [placements]
        else:
            groups = pack_groups_maxrects(
                items,
                atlas_size,
                padding=args.padding,
                scale=args.scale,
                oversize=args.oversize,
                label_height=args.label_height,
                label_gap=args.label_gap,
            )
        data = layout_to_data(
            groups,
            atlas_size,
            padding=args.padding,
            scale=args.scale,
            oversize=args.oversize,
            label_height=args.label_height,
            label_gap=args.label_gap,
        )
        print(json.dumps(data, ensure_ascii=False, indent=2 if args.pretty else None))
    except LayoutError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

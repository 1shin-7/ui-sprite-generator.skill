import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ui-sprite-generator" / "scripts" / "plan_atlas_layout.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("plan_atlas_layout_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def minimal_spec():
    return {
        "schema_version": "1.2",
        "components": [
            {
                "id": "button_primary",
                "resolution_policy": {"target_px": {"w": 100, "h": 40}},
                "atlas_policy": {"group": "buttons"},
            },
            {
                "id": "button_secondary",
                "resolution_policy": {"target_px": {"w": 80, "h": 40}},
                "atlas_policy": {"group": "buttons"},
            },
            {
                "id": "panel_frame",
                "resolution_policy": {"target_px": {"w": 180, "h": 120}},
                "atlas_policy": {"group": "panels"},
            },
        ],
    }


class PlanAtlasLayoutTests(unittest.TestCase):
    def test_packs_simple_items_in_single_atlas(self):
        module = load_script_module()
        items = [
            module.SpriteItem("a", 64, 64),
            module.SpriteItem("b", 32, 32),
            module.SpriteItem("c", 16, 80),
        ]

        placements = module.pack_maxrects(items, (128, 128))

        self.assertEqual({placement.id for placement in placements}, {"a", "b", "c"})
        self.assertTrue(all(placement.atlas_index == 0 for placement in placements))
        self.assertTrue(all(placement.x + placement.w <= 128 for placement in placements))
        self.assertTrue(all(placement.y + placement.h <= 128 for placement in placements))

    def test_groups_into_multiple_atlases_when_needed(self):
        module = load_script_module()
        items = [
            module.SpriteItem("a", 90, 90),
            module.SpriteItem("b", 90, 90),
            module.SpriteItem("c", 90, 90),
        ]

        groups = module.pack_groups_maxrects(items, (128, 128))

        self.assertEqual(len(groups), 3)
        self.assertEqual([placement.atlas_index for group in groups for placement in group], [0, 1, 2])

    def test_extracts_items_from_spec_and_filters_group(self):
        module = load_script_module()

        items = module.items_from_spec(minimal_spec(), component_group="buttons")

        self.assertEqual([item.id for item in items], ["button_primary", "button_secondary"])
        self.assertEqual(items[0].target_w, 100)
        self.assertEqual(items[0].target_h, 40)
        self.assertEqual(items[0].group, "buttons")

    def test_filters_by_repeated_component_id(self):
        module = load_script_module()

        items = module.items_from_spec(
            minimal_spec(),
            component_ids=["panel_frame", "button_primary"],
        )

        self.assertEqual([item.id for item in items], ["button_primary", "panel_frame"])

    def test_padding_expands_cell_but_preserves_content_rect(self):
        module = load_script_module()
        placements = module.pack_maxrects([module.SpriteItem("button", 100, 40)], (160, 120), padding=10)
        placement = placements[0]

        self.assertEqual((placement.w, placement.h), (120, 100))
        self.assertEqual((placement.label_x, placement.label_y), (placement.x + 10, placement.y + 10))
        self.assertEqual((placement.label_w, placement.label_h), (100, 20))
        self.assertEqual((placement.content_x, placement.content_y), (placement.x + 10, placement.y + 50))
        self.assertEqual((placement.content_w, placement.content_h), (100, 40))

    def test_label_height_and_gap_can_be_disabled_for_unlabeled_layouts(self):
        module = load_script_module()
        placements = module.pack_maxrects(
            [module.SpriteItem("button", 100, 40)],
            (160, 120),
            padding=10,
            label_height=0,
            label_gap=0,
        )
        placement = placements[0]

        self.assertEqual((placement.w, placement.h), (120, 60))
        self.assertEqual((placement.label_w, placement.label_h), (0, 0))
        self.assertEqual((placement.content_x, placement.content_y), (placement.x + 10, placement.y + 10))

    def test_long_label_expands_cell_width_and_centers_content(self):
        module = load_script_module()
        placements = module.pack_maxrects(
            [module.SpriteItem("very_long_component_identifier", 40, 20)],
            (512, 128),
            padding=8,
        )
        placement = placements[0]

        self.assertGreater(placement.label_w, placement.content_w)
        self.assertEqual(placement.w, placement.label_w + 16)
        self.assertEqual(placement.label_x, placement.x + 8)
        self.assertGreater(placement.content_x, placement.label_x)

    def test_scale_increases_content_size(self):
        module = load_script_module()
        placements = module.pack_maxrects([module.SpriteItem("button", 100, 40)], (256, 128), scale=2.0)
        placement = placements[0]

        self.assertEqual((placement.content_w, placement.content_h), (200, 80))
        self.assertEqual(placement.requested_scale, 2.0)
        self.assertEqual(placement.effective_scale, 2.0)
        self.assertFalse(placement.clamped)

    def test_default_clamp_downscales_oversized_scaled_item(self):
        module = load_script_module()
        placements = module.pack_maxrects(
            [module.SpriteItem("large_panel", 300, 200)],
            (256, 128),
            padding=8,
            scale=2.0,
        )
        placement = placements[0]

        self.assertTrue(placement.clamped)
        self.assertLess(placement.effective_scale, placement.requested_scale)
        self.assertLessEqual(placement.w, 256)
        self.assertLessEqual(placement.h, 128)
        self.assertEqual((placement.target_w, placement.target_h), (300, 200))

    def test_oversize_fail_rejects_oversized_scaled_item(self):
        module = load_script_module()

        with self.assertRaisesRegex(module.LayoutError, "large_panel"):
            module.pack_maxrects(
                [module.SpriteItem("large_panel", 300, 200)],
                (256, 128),
                padding=8,
                scale=2.0,
                oversize="fail",
            )

    def test_rejects_invalid_inputs_and_empty_selection(self):
        module = load_script_module()

        with self.assertRaisesRegex(module.LayoutError, "atlas dimensions"):
            module.pack_groups_maxrects([module.SpriteItem("a", 1, 1)], (0, 128))
        with self.assertRaisesRegex(module.LayoutError, "padding"):
            module.pack_groups_maxrects([module.SpriteItem("a", 1, 1)], (128, 128), padding=-1)
        with self.assertRaisesRegex(module.LayoutError, "scale"):
            module.pack_groups_maxrects([module.SpriteItem("a", 1, 1)], (128, 128), scale=0)
        with self.assertRaisesRegex(module.LayoutError, "no components selected"):
            module.items_from_spec(minimal_spec(), component_group="missing")

    def test_rejects_duplicate_component_ids(self):
        module = load_script_module()
        spec = minimal_spec()
        spec["components"].append(spec["components"][0].copy())

        with self.assertRaisesRegex(module.LayoutError, "duplicate component id"):
            module.items_from_spec(spec)

    def test_cli_outputs_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = Path(tmp) / "spec.json"
            spec_path.write_text(json.dumps(minimal_spec()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--from-spec",
                    str(spec_path),
                    "--atlas",
                    "256x128",
                    "--component-group",
                    "buttons",
                    "--padding",
                    "4",
                ],
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["atlas_size"], [256, 128])
        self.assertEqual(data["padding"], 4)
        self.assertEqual(data["label_height"], 20)
        self.assertEqual(data["label_gap"], 20)
        self.assertEqual(data["atlases"][0]["placements"][0]["id"], "button_primary")

    def test_cli_pretty_outputs_indented_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = Path(tmp) / "spec.json"
            spec_path.write_text(json.dumps(minimal_spec()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--from-spec",
                    str(spec_path),
                    "--atlas",
                    "256x128",
                    "--pretty",
                ],
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("\n  \"atlas_size\"", result.stdout)


if __name__ == "__main__":
    unittest.main()

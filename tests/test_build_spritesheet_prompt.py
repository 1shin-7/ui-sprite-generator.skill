import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ui-sprite-generator" / "scripts" / "build_spritesheet_prompt.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_spritesheet_prompt_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_spec():
    return {
        "schema_version": "1.1",
        "source_image": {"path": "input/effect.png", "width": 800, "height": 600},
        "style": {
            "description": "flat toy game UI",
            "ui_style": "rounded matte dark panels, clean gray buttons, amber badges",
            "background_style": "blue patterned wallpaper behind the UI",
            "palette": ["charcoal", "cream", "amber"],
            "materials": ["flat rubber button", "matte panel"],
            "lighting": "soft highlights",
            "ornament_language": "rounded capsules",
            "negative_constraints": ["no painterly noise", "no extra icons"],
        },
        "background": {
            "description": "blue background",
            "visible_regions": [{"id": "bg", "bbox": {"x": 0, "y": 0, "w": 800, "h": 600}}],
            "occluded_regions": [],
            "mask_strategy": "remove UI",
        },
        "components": [
            {
                "id": "flat_button",
                "role": "icon_button",
                "source_bbox": {"x": 40, "y": 50, "w": 120, "h": 48},
                "visual_description": "clean gray rounded button with dark rim",
                "attached_decorations": [],
                "center": "filled",
                "surface_policy": "flat_fill",
                "occlusion": {
                    "status": "unoccluded",
                    "occluders": [],
                    "reconstruction": "redraw as visible",
                },
                "render_pattern": "background_image",
                "resolution_policy": {
                    "minimum_source_scale": 1,
                    "recommended_generation_scale": 2,
                    "target_px": {"w": 240, "h": 96},
                    "allow_downscale": False,
                },
                "atlas_policy": {"group": "buttons", "can_share_sheet": True, "minimum_gutter": 32},
                "layering": {"z_index": 10, "anchor": "top_left"},
                "states": ["default"],
                "companions": [],
            },
            {
                "id": "covered_panel",
                "role": "panel_frame",
                "source_bbox": {"x": 180, "y": 50, "w": 280, "h": 180},
                "visual_description": "dark rounded panel partly covered by a text badge in the source",
                "attached_decorations": ["soft shadow"],
                "center": "hollow",
                "surface_policy": "hollow",
                "occlusion": {
                    "status": "partially_occluded",
                    "occluders": ["floating text badge"],
                    "reconstruction": "redraw the full unobstructed panel frame",
                },
                "render_pattern": "nine_slice",
                "resolution_policy": {
                    "minimum_source_scale": 1,
                    "recommended_generation_scale": 2,
                    "target_px": {"w": 560, "h": 360},
                    "allow_downscale": False,
                },
                "atlas_policy": {"group": "panels", "can_share_sheet": True, "minimum_gutter": 32},
                "layering": {"z_index": 8, "anchor": "top_left"},
                "states": ["default"],
                "companions": [],
            },
            {
                "id": "exp_bar_fill",
                "role": "bar_fill_texture",
                "source_bbox": {"x": 80, "y": 260, "w": 280, "h": 24},
                "visual_description": "blue flat-to-soft gradient fill inside the experience bar",
                "attached_decorations": [],
                "center": "filled",
                "surface_policy": "textured_fill",
                "occlusion": {
                    "status": "partially_occluded",
                    "occluders": ["ornate bar frame ends"],
                    "reconstruction": "redraw as a full rectangular fill texture hidden below the frame",
                },
                "render_pattern": "linear_clip",
                "resolution_policy": {
                    "minimum_source_scale": 1,
                    "recommended_generation_scale": 2,
                    "target_px": {"w": 560, "h": 48},
                    "allow_downscale": False,
                },
                "atlas_policy": {"group": "bars", "can_share_sheet": True, "minimum_gutter": 24},
                "layering": {"z_index": 7, "anchor": "top_left"},
                "states": ["default"],
                "companions": ["exp_bar_track"],
            },
        ],
    }


class BuildSpritesheetPromptTests(unittest.TestCase):
    def test_help_exposes_spritesheet_controls(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--sheet-mode", result.stdout)
        self.assertIn("--max-fill-ratio", result.stdout)
        self.assertIn("--component-group", result.stdout)
        self.assertIn("--component-id", result.stdout)
        self.assertIn("--canvas-size", result.stdout)

    def test_builds_labeled_solid_key_spritesheet_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            spec_path = work / "spec.json"
            out_path = work / "spritesheet.md"
            spec_path.write_text(json.dumps(minimal_spec()), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--spec", str(spec_path), "--output", str(out_path)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            content = out_path.read_text(encoding="utf-8").lower()
            self.assertIn("# ui spritesheet generation prompt", content)
            self.assertIn("solid `#e0e0e0`", content)
            self.assertIn("print each component id", content)
            self.assertIn("outside and above", content)
            self.assertIn("label must not overlap", content)
            self.assertIn("flat_button", content)
            self.assertIn("surface_policy: flat_fill", content)
            self.assertIn("do not add painterly texture", content)
            self.assertIn("max_generation_scale", content)
            self.assertIn("do not increase target_px", content)
            self.assertIn("covered_panel", content)
            self.assertIn("redraw the full unobstructed", content)
            self.assertIn("exp_bar_fill", content)
            self.assertIn("full rectangular fill texture", content)
            self.assertIn("do not infer a non-rectangular silhouette", content)

    def test_transparent_mode_changes_background_contract(self):
        module = load_script_module()
        prompt = module.build_prompt(minimal_spec(), sheet_mode="transparent")

        self.assertIn("transparent RGBA canvas", prompt)
        self.assertNotIn("solid `#e0e0e0`", prompt)

    def test_overpacked_sheet_warns_to_split_without_changing_target_px(self):
        module = load_script_module()
        spec = minimal_spec()

        prompt = module.build_prompt(spec, canvas_size="256x256", max_fill_ratio=0.65)

        self.assertIn("Selected components exceed the fill budget", prompt)
        self.assertIn("split this request into smaller sheets", prompt)
        self.assertIn("Do not increase target_px", prompt)
        self.assertIn("target_px: 240x96", prompt)

    def test_filters_components_by_group(self):
        module = load_script_module()
        prompt = module.build_prompt(minimal_spec(), component_group="buttons")

        self.assertIn("flat_button", prompt)
        self.assertNotIn("covered_panel", prompt)


if __name__ == "__main__":
    unittest.main()

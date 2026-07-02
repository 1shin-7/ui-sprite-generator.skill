import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ui-sprite-generator" / "scripts" / "build_atlas_prompt.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_atlas_prompt_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_spec():
    return {
        "schema_version": "1.2",
        "source_image": {"path": "effect.png", "width": 800, "height": 600},
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
                "states": ["default"],
                "companions": [],
            },
            {
                "id": "covered_panel",
                "role": "panel_frame",
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
                "states": ["default"],
                "companions": [],
            },
            {
                "id": "exp_bar_fill",
                "role": "bar_fill_texture",
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
                "states": ["default"],
                "companions": ["exp_bar_track"],
            },
        ],
        "instances": [
            {
                "id": "flat_button_left",
                "uses": "flat_button",
                "source_bbox": {"x": 40, "y": 50, "w": 120, "h": 48},
                "layering": {"z_index": 10, "anchor": "top_left"},
            },
            {
                "id": "flat_button_right",
                "uses": "flat_button",
                "source_bbox": {"x": 180, "y": 50, "w": 120, "h": 48},
                "layering": {"z_index": 10, "anchor": "top_left"},
            },
            {
                "id": "covered_panel_main",
                "uses": "covered_panel",
                "source_bbox": {"x": 180, "y": 50, "w": 280, "h": 180},
                "layering": {"z_index": 8, "anchor": "top_left"},
            },
            {
                "id": "exp_bar_fill_main",
                "uses": "exp_bar_fill",
                "source_bbox": {"x": 80, "y": 260, "w": 280, "h": 24},
                "layering": {"z_index": 7, "anchor": "top_left"},
            },
        ],
    }


def extract_local_atlas_spec(prompt):
    start = prompt.index("## Local Atlas Spec JSON")
    fence_start = prompt.index("```json", start) + len("```json")
    fence_end = prompt.index("```", fence_start)
    return json.loads(prompt[fence_start:fence_end].strip())


class BuildAtlasPromptTests(unittest.TestCase):
    def test_help_exposes_atlas_controls(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--atlas-bg", result.stdout)
        self.assertIn("--atlas-key-color", result.stdout)
        self.assertNotIn("--sheet-mode", result.stdout)
        self.assertIn("--max-fill-ratio", result.stdout)
        self.assertIn("--component-group", result.stdout)
        self.assertIn("--component-id", result.stdout)
        self.assertIn("--canvas-size", result.stdout)
        self.assertIn("--layout-strategy", result.stdout)
        self.assertIn("--layout-padding", result.stdout)
        self.assertIn("--layout-scale", result.stdout)
        self.assertIn("--oversize", result.stdout)

    def test_builds_labeled_chroma_key_atlas_prompt_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            spec_path = work / "spec.json"
            out_path = work / "atlas.md"
            spec_path.write_text(json.dumps(minimal_spec()), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--spec", str(spec_path), "--output", str(out_path)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            content = out_path.read_text(encoding="utf-8").lower()
            self.assertIn("# ui atlas generation prompt", content)
            self.assertIn("atlas_bg: chroma-key", content)
            self.assertIn("atlas_key_color: #00ff00", content)
            self.assertIn("single flat chroma key `#00ff00`", content)
            self.assertNotIn("solid `#e0e0e0`", content)
            self.assertIn("print each component id", content)
            self.assertIn("outside and above", content)
            self.assertIn("label must not overlap", content)
            self.assertIn("flat_button", content)
            self.assertIn("source_instances", content)
            self.assertIn("flat_button_left", content)
            self.assertIn("flat_button_right", content)
            self.assertIn("surface_policy: flat_fill", content)
            self.assertIn("do not add painterly texture", content)
            self.assertIn("max_detail_scale_limit", content)
            self.assertIn("do not increase target_px", content)
            self.assertIn("maxrects layout guidance", content)
            self.assertIn("follow maxrects layout guidance", content)
            self.assertIn("layout_strategy: maxrects", content)
            self.assertIn("atlas_index=0", content)
            self.assertIn("label=(x=", content)
            self.assertIn("label_gap=20", content)
            self.assertIn("content_w=240", content)
            self.assertNotIn("loose grid", content)
            self.assertIn("covered_panel", content)
            self.assertIn("redraw the full unobstructed", content)
            self.assertIn("exp_bar_fill", content)
            self.assertIn("full rectangular fill texture", content)
            self.assertIn("do not infer a non-rectangular silhouette", content)

    def test_prompt_embeds_local_complete_atlas_spec_for_selected_components(self):
        module = load_script_module()
        prompt = module.build_prompt(
            minimal_spec(),
            atlas_bg="transparent",
            component_group="buttons",
            canvas_size="1024x1536",
            max_fill_ratio=0.5,
        )
        local_spec = extract_local_atlas_spec(prompt)

        self.assertEqual(local_spec["schema_version"], "1.2")
        self.assertEqual(local_spec["source_image"], {"path": "effect.png", "width": 800, "height": 600})
        self.assertEqual(local_spec["atlas_context"]["atlas_bg"], "transparent")
        self.assertEqual(local_spec["atlas_context"]["atlas_key_color"], "#00ff00")
        self.assertEqual(local_spec["atlas_context"]["canvas_size"], "1024x1536")
        self.assertEqual(local_spec["atlas_context"]["layout_strategy"], "maxrects")
        self.assertNotIn("max_fill_ratio", local_spec["atlas_context"])
        self.assertNotIn("over_budget", local_spec["atlas_context"])
        self.assertIn("layout", local_spec["atlas_context"])
        self.assertEqual(local_spec["atlas_context"]["layout"]["padding"], 24)
        self.assertEqual(local_spec["atlas_context"]["layout"]["label_height"], 20)
        self.assertEqual(local_spec["atlas_context"]["layout"]["label_gap"], 20)
        self.assertEqual(local_spec["atlas_context"]["layout"]["requested_scale"], 1.0)
        placement = local_spec["atlas_context"]["layout"]["atlases"][0]["placements"][0]
        self.assertEqual(placement["id"], "flat_button")
        self.assertEqual(placement["label_h"], 20)
        self.assertEqual(placement["content_y"], placement["y"] + 24 + 20 + 20)
        self.assertEqual([component["id"] for component in local_spec["components"]], ["flat_button"])
        self.assertEqual(
            [instance["id"] for instance in local_spec["instances"]],
            ["flat_button_left", "flat_button_right"],
        )
        self.assertNotIn("background", local_spec)
        self.assertNotIn("covered_panel", json.dumps(local_spec))

    def test_transparent_mode_requires_true_alpha_and_forbids_fake_transparency(self):
        module = load_script_module()
        prompt = module.build_prompt(minimal_spec(), atlas_bg="transparent")

        self.assertIn("true transparent RGBA canvas", prompt)
        self.assertIn("0% alpha", prompt)
        self.assertIn("checkerboard", prompt)
        self.assertIn("grid", prompt)
        self.assertIn("fake transparency", prompt)
        self.assertNotIn("solid `#e0e0e0`", prompt)
        self.assertNotIn("single flat chroma key", prompt)

    def test_solid_key_mode_keeps_legacy_gray_key_contract(self):
        module = load_script_module()
        prompt = module.build_prompt(minimal_spec(), atlas_bg="solid-key")

        self.assertIn("atlas_bg: solid-key", prompt)
        self.assertIn("solid `#e0e0e0`", prompt)
        self.assertNotIn("single flat chroma key", prompt)

    def test_custom_chroma_key_color_is_embedded_in_prompt_and_local_spec(self):
        module = load_script_module()
        prompt = module.build_prompt(minimal_spec(), atlas_key_color="#ff00ff")
        local_spec = extract_local_atlas_spec(prompt)

        self.assertIn("single flat chroma key `#ff00ff`", prompt)
        self.assertEqual(local_spec["atlas_context"]["atlas_bg"], "chroma-key")
        self.assertEqual(local_spec["atlas_context"]["atlas_key_color"], "#ff00ff")

    def test_rejects_invalid_chroma_key_color(self):
        module = load_script_module()

        with self.assertRaisesRegex(module.PromptBuildError, "invalid atlas key color"):
            module.build_prompt(minimal_spec(), atlas_key_color="green")

    def test_overpacked_atlas_warns_to_split_without_changing_target_px(self):
        module = load_script_module()
        prompt = module.build_prompt(
            minimal_spec(),
            canvas_size="256x256",
            max_fill_ratio=0.65,
            layout_strategy="area-budget",
        )

        self.assertIn("Selected components exceed the fill budget", prompt)
        self.assertIn("split this request into smaller atlas sheets", prompt)
        self.assertIn("Do not increase target_px", prompt)
        self.assertIn("target_px: 240x96", prompt)
        local_spec = extract_local_atlas_spec(prompt)
        self.assertEqual(local_spec["atlas_context"]["layout_strategy"], "area-budget")
        self.assertEqual(local_spec["atlas_context"]["legacy_budget"]["max_fill_ratio"], 0.65)
        self.assertEqual(prompt.count("### 1. `flat_button`"), 1)

    def test_maxrects_layout_clamps_oversized_default_without_area_budget_warning(self):
        module = load_script_module()
        prompt = module.build_prompt(
            minimal_spec(),
            component_group="panels",
            canvas_size="256x256",
            layout_padding=8,
            layout_scale=2.0,
        )
        local_spec = extract_local_atlas_spec(prompt)
        placement = local_spec["atlas_context"]["layout"]["atlases"][0]["placements"][0]

        self.assertIn("MaxRects clamped", prompt)
        self.assertTrue(placement["clamped"])
        self.assertEqual(placement["requested_scale"], 2.0)
        self.assertLess(placement["effective_scale"], 2.0)
        self.assertNotIn("Selected components exceed the fill budget", prompt)

    def test_filters_components_by_group(self):
        module = load_script_module()
        prompt = module.build_prompt(minimal_spec(), component_group="buttons")

        self.assertIn("flat_button", prompt)
        self.assertNotIn("covered_panel", prompt)

    def test_rejects_source_pixel_component_contract(self):
        module = load_script_module()
        spec = minimal_spec()
        spec["components"][0]["occlusion"][
            "reconstruction"
        ] = "Extracted directly from the source pixels for this component split run."
        spec["components"][0]["states"] = ["source"]

        with self.assertRaisesRegex(module.PromptBuildError, "source-derived atlas art"):
            module.build_prompt(spec)


if __name__ == "__main__":
    unittest.main()

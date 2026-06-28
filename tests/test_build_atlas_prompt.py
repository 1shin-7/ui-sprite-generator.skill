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
        "schema_version": "1.0",
        "source_image": {"path": "input/effect.png", "width": 800, "height": 600},
        "style": {
            "description": "ornate fantasy UI",
            "palette": ["gold", "jade"],
            "materials": ["polished metal", "translucent glass"],
            "lighting": "soft rim glow",
            "ornament_language": "filigree corners",
            "negative_constraints": ["no text"],
        },
        "background": {
            "description": "painted background",
            "visible_regions": [{"id": "bg", "bbox": {"x": 0, "y": 0, "w": 800, "h": 600}}],
            "occluded_regions": [],
            "mask_strategy": "inpaint foreground UI",
        },
        "components": [
            {
                "id": "main_frame",
                "role": "panel frame",
                "source_bbox": {"x": 10, "y": 20, "w": 400, "h": 300},
                "visual_description": "ornate hollow frame",
                "attached_decorations": ["corner trim"],
                "center": "hollow",
                "render_pattern": "nine_slice",
                "resolution_policy": {
                    "minimum_source_scale": 1,
                    "recommended_generation_scale": 2,
                    "target_px": {"w": 800, "h": 600},
                    "allow_downscale": False,
                },
                "atlas_policy": {"group": "panels", "can_share_sheet": True, "minimum_gutter": 32},
                "layering": {"z_index": 10, "anchor": "top_left"},
                "states": ["default"],
                "companions": [],
            },
            {
                "id": "bar_fill",
                "role": "progress fill",
                "source_bbox": {"x": 30, "y": 500, "w": 300, "h": 30},
                "visual_description": "luminous fill texture",
                "attached_decorations": [],
                "center": "filled",
                "render_pattern": "linear_clip",
                "resolution_policy": {
                    "minimum_source_scale": 1,
                    "recommended_generation_scale": 2,
                    "target_px": {"w": 600, "h": 60},
                    "allow_downscale": False,
                },
                "atlas_policy": {"group": "bars", "can_share_sheet": True, "minimum_gutter": 24},
                "layering": {"z_index": 20, "anchor": "top_left"},
                "states": ["default"],
                "companions": ["bar_track"],
            },
        ],
    }


class BuildAtlasPromptTests(unittest.TestCase):
    def test_help_exposes_programmatic_prompt_controls(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--spec", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertIn("--atlas-mode", result.stdout)
        self.assertIn("--component-group", result.stdout)
        self.assertIn("--component-id", result.stdout)
        self.assertIn("--canvas-size", result.stdout)
        self.assertIn("--include-raw-json", result.stdout)

    def test_builds_markdown_prompt_with_contract_and_spec_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            spec_path = work / "spec.json"
            out_path = work / "ui_atlas.md"
            spec_path.write_text(json.dumps(minimal_spec()), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--spec", str(spec_path), "--output", str(out_path)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            content = out_path.read_text(encoding="utf-8")
            self.assertIn("# UI Atlas Generation Prompt", content)
            self.assertIn("## Redraw Contract", content)
            self.assertIn("## Atlas Rules", content)
            self.assertIn("```json", content)
            self.assertIn("main_frame", content)
            self.assertIn("center: hollow", content)
            self.assertIn("render_pattern: nine_slice", content)
            self.assertIn("target_px: 800x600", content)
            self.assertIn("minimum_gutter: 32", content)
            self.assertIn("hollow or transparent centers must remain empty", content.lower())

    def test_filters_by_group_and_component_ids(self):
        module = load_script_module()
        spec = minimal_spec()

        group_prompt = module.build_prompt(spec, component_group="bars")
        id_prompt = module.build_prompt(spec, component_ids=["main_frame"])

        self.assertIn('`bar_fill`', group_prompt)
        self.assertNotIn('`main_frame`', group_prompt)
        self.assertIn('`main_frame`', id_prompt)
        self.assertNotIn('`bar_fill`', id_prompt)
        self.assertNotIn('"id": "bar_fill"', id_prompt)

    def test_prompt_is_generic_not_style_hardcoded(self):
        module = load_script_module()
        prompt = module.CANONICAL_PROMPT.lower()

        self.assertNotIn("xianxia", prompt)
        self.assertNotIn("mountain", prompt)
        self.assertNotIn("cloud pattern", prompt)


if __name__ == "__main__":
    unittest.main()

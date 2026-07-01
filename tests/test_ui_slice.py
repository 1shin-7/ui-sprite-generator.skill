import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "ui-sprite-generator"
SCRIPT = PACKAGE / "scripts" / "ui_slice.py"


class UiSliceTests(unittest.TestCase):
    def write_per_atlas_map(self, path, atlas_file, sprites):
        path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "atlas": {"id": path.stem.removesuffix(".map"), "file": atlas_file},
                    "sprites": sprites,
                }
            ),
            encoding="utf-8",
        )

    def test_slices_multiple_per_atlas_maps_from_atlas_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            atlas_dir = work / "atlas"
            atlas_dir.mkdir()
            Image.new("RGBA", (16, 16), (10, 20, 30, 255)).save(atlas_dir / "buttons_01.png")
            Image.new("RGBA", (16, 16), (40, 50, 60, 255)).save(atlas_dir / "panels_01.png")
            self.write_per_atlas_map(
                atlas_dir / "buttons_01.map.json",
                "buttons_01.png",
                [{"id": "button", "filename": "button.png", "bbox": {"x": 0, "y": 0, "w": 8, "h": 8}}],
            )
            self.write_per_atlas_map(
                atlas_dir / "panels_01.map.json",
                "panels_01.png",
                [{"id": "panel", "filename": "panel.png", "bbox": {"x": 8, "y": 8, "w": 8, "h": 8}}],
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--atlas-dir", str(atlas_dir), "--out", str(work / "sprites")],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((work / "sprites" / "button.png").is_file())
            self.assertTrue((work / "sprites" / "panel.png").is_file())

    def test_per_atlas_maps_reject_duplicate_sprite_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            atlas_dir = work / "atlas"
            atlas_dir.mkdir()
            Image.new("RGBA", (16, 16), (10, 20, 30, 255)).save(atlas_dir / "buttons_01.png")
            Image.new("RGBA", (16, 16), (40, 50, 60, 255)).save(atlas_dir / "panels_01.png")
            sprite = {"id": "button", "filename": "button.png", "bbox": {"x": 0, "y": 0, "w": 8, "h": 8}}
            self.write_per_atlas_map(atlas_dir / "buttons_01.map.json", "buttons_01.png", [sprite])
            self.write_per_atlas_map(
                atlas_dir / "panels_01.map.json",
                "panels_01.png",
                [{**sprite, "filename": "button_alt.png"}],
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--atlas-dir", str(atlas_dir), "--out", str(work / "sprites")],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate sprite id: button", result.stderr)

    def test_per_atlas_maps_require_matching_atlas_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            atlas_dir = work / "atlas"
            atlas_dir.mkdir()
            self.write_per_atlas_map(
                atlas_dir / "buttons_01.map.json",
                "buttons_01.png",
                [{"id": "button", "filename": "button.png", "bbox": {"x": 0, "y": 0, "w": 8, "h": 8}}],
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--atlas-dir", str(atlas_dir), "--out", str(work / "sprites")],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("atlas file not found", result.stderr)

    def test_rejects_out_of_bounds_bbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            atlas = work / "atlas.png"
            Image.new("RGBA", (16, 16), (255, 255, 255, 255)).save(atlas)
            atlas_map = work / "atlas_map.json"
            atlas_map.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "atlases": [{"id": "atlas", "file": str(atlas)}],
                        "sprites": [
                            {
                                "id": "bad",
                                "atlas": "atlas",
                                "filename": "bad.png",
                                "bbox": {"x": 12, "y": 0, "w": 8, "h": 8},
                                "display_size": {"w": 8, "h": 8},
                                "render_pattern": "background_image",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--map", str(atlas_map), "--out", str(work / "sprites")],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("out of bounds", result.stderr)

    def test_border_connected_background_removal_preserves_internal_white(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            atlas = work / "atlas.png"
            image = Image.new("RGBA", (12, 12), (255, 255, 255, 255))
            pixels = image.load()
            for y in range(3, 9):
                for x in range(3, 9):
                    pixels[x, y] = (20, 30, 40, 255)
            pixels[5, 5] = (255, 255, 255, 255)
            image.save(atlas)

            atlas_map = work / "atlas_map.json"
            atlas_map.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "atlases": [{"id": "atlas", "file": str(atlas)}],
                        "sprites": [
                            {
                                "id": "item",
                                "atlas": "atlas",
                                "filename": "item.png",
                                "bbox": {"x": 0, "y": 0, "w": 12, "h": 12},
                                "display_size": {"w": 12, "h": 12},
                                "render_pattern": "background_image",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--map",
                    str(atlas_map),
                    "--out",
                    str(work / "sprites"),
                    "--bg-policy",
                    "transparentize-border",
                    "--bg-color",
                    "#ffffff",
                    "--bg-tolerance",
                    "0",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = Image.open(work / "sprites" / "item.png").convert("RGBA")
            self.assertEqual(output.getpixel((0, 0))[3], 0)
            self.assertEqual(output.getpixel((5, 5)), (255, 255, 255, 255))

    def test_solid_key_atlas_background_can_be_removed_without_label_in_crop(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            atlas = work / "atlas.png"
            image = Image.new("RGBA", (80, 60), (224, 224, 224, 255))
            pixels = image.load()
            for y in range(20, 44):
                for x in range(10, 50):
                    pixels[x, y] = (60, 60, 60, 255)
            for x in range(20, 40):
                pixels[x, 10] = (120, 120, 120, 255)
            image.save(atlas)

            atlas_map = work / "atlas_map.json"
            atlas_map.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "root_size": {"w": 800, "h": 600},
                        "atlases": [{"id": "sheet", "file": str(atlas)}],
                        "sprites": [
                            {
                                "id": "button",
                                "atlas": "sheet",
                                "filename": "button.png",
                                "bbox": {"x": 8, "y": 18, "w": 44, "h": 28},
                                "display_size": {"w": 22, "h": 14},
                                "source_bbox": {"x": 100, "y": 100, "w": 22, "h": 14},
                                "z_index": 1,
                                "render_pattern": "background_image",
                                "render_params": {},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--map",
                    str(atlas_map),
                    "--out",
                    str(work / "sprites"),
                    "--bg-policy",
                    "transparentize-border",
                    "--bg-color",
                    "#e0e0e0",
                    "--bg-tolerance",
                    "0",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = Image.open(work / "sprites" / "button.png").convert("RGBA")
            self.assertEqual(output.getpixel((0, 0))[3], 0)
            self.assertEqual(output.getpixel((12, 12)), (60, 60, 60, 255))
            colors = [output.getpixel((x, y)) for y in range(output.height) for x in range(output.width)]
            self.assertNotIn((120, 120, 120, 255), colors)

    def test_accepts_yaml_atlas_map_when_pyyaml_is_available(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML is not installed")

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            atlas = work / "atlas.png"
            Image.new("RGBA", (16, 16), (40, 50, 60, 255)).save(atlas)
            atlas_map = work / "atlas_map.yaml"
            atlas_map.write_text(
                "\n".join(
                    [
                        "schema_version: '1.0'",
                        "atlases:",
                        f"  - id: sheet\n    file: {atlas.as_posix()}",
                        "sprites:",
                        "  - id: item",
                        "    atlas: sheet",
                        "    filename: item.png",
                        "    bbox: {x: 0, y: 0, w: 16, h: 16}",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--map", str(atlas_map), "--out", str(work / "sprites")],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((work / "sprites" / "item.png").is_file())


if __name__ == "__main__":
    unittest.main()

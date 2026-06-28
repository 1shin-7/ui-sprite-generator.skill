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


if __name__ == "__main__":
    unittest.main()

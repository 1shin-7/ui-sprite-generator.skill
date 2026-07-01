import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ui-sprite-generator" / "scripts" / "build_render_manifest.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_render_manifest_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_spec():
    return {
        "schema_version": "1.2",
        "source_image": {"path": "effect.png", "width": 800, "height": 600},
        "style": {"description": "verbose style text should not leak"},
        "components": [
            {
                "id": "bar_fill",
                "role": "progress fill",
                "visual_description": "long text should not leak",
                "occlusion": {"reconstruction": "long text should not leak"},
                "render_pattern": "linear_clip",
                "render_params": {"axis": "x", "value": 1.0},
                "companions": ["bar_track"],
                "resolution_policy": {"target_px": {"w": 600, "h": 60}},
            },
            {
                "id": "bar_track",
                "role": "track",
                "visual_description": "long text should not leak",
                "render_pattern": "background_image",
                "companions": [],
            },
        ],
        "instances": [
            {
                "id": "bar_fill_primary",
                "uses": "bar_fill",
                "source_bbox": {"x": 30, "y": 500, "w": 300, "h": 30},
                "layering": {"z_index": 20, "anchor": "top_left"},
            },
            {
                "id": "bar_fill_secondary",
                "uses": "bar_fill",
                "source_bbox": {"x": 360, "y": 500, "w": 300, "h": 30},
                "layering": {"z_index": 20, "anchor": "top_left"},
                "render_params_override": {"value": 0.5},
            },
            {
                "id": "bar_track_primary",
                "uses": "bar_track",
                "source_bbox": {"x": 30, "y": 500, "w": 300, "h": 30},
                "layering": {"z_index": 10, "anchor": "top_left"},
            },
        ],
    }


def minimal_atlas_map():
    return {
        "schema_version": "1.0",
        "atlases": [{"id": "sheet", "file": "spritesheet/sheet.png"}],
        "sprites": [
            {
                "id": "bar_fill",
                "atlas": "sheet",
                "filename": "bar_fill.png",
                "bbox": {"x": 5, "y": 6, "w": 70, "h": 12},
                "source_bbox": {"x": 999, "y": 999, "w": 1, "h": 1},
                "z_index": 999,
                "render_pattern": "background_image",
                "render_params": {"wrong": True},
            },
            {
                "id": "bar_track",
                "atlas": "sheet",
                "filename": "bar_track.png",
                "bbox": {"x": 80, "y": 6, "w": 70, "h": 12},
            },
        ],
    }


class BuildRenderManifestTests(unittest.TestCase):
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

    def test_builds_compact_manifest_from_spec_layout_and_atlas_assets(self):
        module = load_script_module()

        manifest = module.build_render_manifest(
            minimal_spec(),
            minimal_atlas_map(),
            background="background_plate.png",
            sprites_dir="sprites",
        )

        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["root_size"], {"w": 800, "h": 600})
        self.assertEqual(manifest["background"], {"file": "background_plate.png"})
        fill = manifest["sprites"][0]
        self.assertEqual(fill["id"], "bar_fill_primary")
        self.assertEqual(fill["component"], "bar_fill")
        self.assertEqual(fill["file"], "sprites/bar_fill.png")
        self.assertEqual(fill["x"], 30)
        self.assertEqual(fill["y"], 500)
        self.assertEqual(fill["w"], 300)
        self.assertEqual(fill["h"], 30)
        self.assertEqual(fill["z_index"], 20)
        self.assertEqual(fill["render_pattern"], "linear_clip")
        self.assertEqual(fill["render_params"], {"axis": "x", "value": 1.0})
        self.assertEqual(fill["companions"], ["bar_track"])
        self.assertEqual(manifest["sprites"][1]["id"], "bar_fill_secondary")
        self.assertEqual(manifest["sprites"][1]["render_params"], {"axis": "x", "value": 0.5})
        self.assertNotIn("visual_description", json.dumps(manifest))
        self.assertNotIn("resolution_policy", json.dumps(manifest))
        self.assertNotIn("bbox", fill)

    def test_cli_writes_json_compat_render_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            spec_path = work / "spec.json"
            atlas_path = work / "atlas_map.json"
            out_path = work / "render.json"
            spec_path.write_text(json.dumps(minimal_spec()), encoding="utf-8")
            atlas_path.write_text(json.dumps(minimal_atlas_map()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--spec",
                    str(spec_path),
                    "--atlas-map",
                    str(atlas_path),
                    "--output",
                    str(out_path),
                    "--background",
                    "background_plate.png",
                    "--sprites-dir",
                    "sprites",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["sprites"][0]["file"], "sprites/bar_fill.png")

    def test_cli_builds_render_manifest_from_per_atlas_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            atlas_dir = work / "atlas"
            atlas_dir.mkdir()
            (atlas_dir / "bars_01.png").write_bytes(b"fake image")
            spec_path = work / "spec.json"
            out_path = work / "render.json"
            spec_path.write_text(json.dumps(minimal_spec()), encoding="utf-8")
            self.write_per_atlas_map(
                atlas_dir / "bars_01.map.json",
                "bars_01.png",
                [
                    {"id": "bar_fill", "filename": "bar_fill.png", "bbox": {"x": 5, "y": 6, "w": 70, "h": 12}},
                    {"id": "bar_track", "filename": "bar_track.png", "bbox": {"x": 80, "y": 6, "w": 70, "h": 12}},
                ],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--spec",
                    str(spec_path),
                    "--atlas-dir",
                    str(atlas_dir),
                    "--output",
                    str(out_path),
                    "--background",
                    "background_plate.png",
                    "--sprites-dir",
                    "sprites",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["sprites"][0]["file"], "sprites/bar_fill.png")
            self.assertEqual(data["sprites"][0]["z_index"], 20)

    def test_fails_when_spec_component_has_no_sprite_asset(self):
        module = load_script_module()
        atlas_map = minimal_atlas_map()
        atlas_map["sprites"] = [atlas_map["sprites"][0]]

        with self.assertRaisesRegex(module.RenderManifestError, "missing sprite asset"):
            module.build_render_manifest(minimal_spec(), atlas_map)

    def test_fails_with_clear_error_for_invalid_spec_render_fields(self):
        module = load_script_module()
        spec = minimal_spec()
        spec["instances"][0]["source_bbox"] = {"x": 30, "y": 500}

        with self.assertRaisesRegex(module.RenderManifestError, "bar_fill_primary: invalid render fields"):
            module.build_render_manifest(spec, minimal_atlas_map())

    def test_fails_when_sprite_asset_is_not_present_in_spec(self):
        module = load_script_module()
        atlas_map = minimal_atlas_map()
        atlas_map["sprites"].append(
            {
                "id": "extra_asset",
                "atlas": "sheet",
                "filename": "extra_asset.png",
                "bbox": {"x": 1, "y": 1, "w": 2, "h": 2},
            }
        )

        with self.assertRaisesRegex(module.RenderManifestError, "sprite asset not present in spec"):
            module.build_render_manifest(minimal_spec(), atlas_map)

    def test_fails_when_instance_references_unknown_component(self):
        module = load_script_module()
        spec = minimal_spec()
        spec["instances"][0]["uses"] = "unknown_component"

        with self.assertRaisesRegex(module.RenderManifestError, "unknown component"):
            module.build_render_manifest(spec, minimal_atlas_map())

    def test_rejects_legacy_spec_version(self):
        module = load_script_module()
        spec = minimal_spec()
        spec["schema_version"] = "1.1"

        with self.assertRaisesRegex(module.RenderManifestError, "spec.schema_version must be 1.2"):
            module.build_render_manifest(spec, minimal_atlas_map())


if __name__ == "__main__":
    unittest.main()

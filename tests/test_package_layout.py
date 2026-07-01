from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackageLayoutTests(unittest.TestCase):
    def test_skill_is_directory_package_not_root_single_file(self):
        package = ROOT / "ui-sprite-generator"

        self.assertFalse((ROOT / "SKILL.md").exists())
        self.assertTrue((package / "SKILL.md").is_file())
        self.assertTrue((package / "prompts").is_dir())
        self.assertTrue((package / "schemas").is_dir())
        self.assertTrue((package / "scripts").is_dir())
        self.assertTrue((package / "prompts" / "03_generate_ui_atlas.md").is_file())
        self.assertTrue((package / "prompts" / "04_verify_ui_atlas.md").is_file())
        self.assertFalse((package / "prompts" / "03_generate_spritesheet.md").exists())
        self.assertFalse((package / "prompts" / "04_verify_spritesheet.md").exists())
        self.assertTrue((package / "scripts" / "build_atlas_prompt.py").is_file())
        self.assertTrue((package / "scripts" / "plan_atlas_layout.py").is_file())
        self.assertFalse((package / "scripts" / "build_spritesheet_prompt.py").exists())
        self.assertTrue((package / "scripts" / "build_render_manifest.py").is_file())
        self.assertTrue((package / "scripts" / "data_io.py").is_file())
        self.assertTrue((package / "scripts" / "atlas_maps.py").is_file())
        self.assertTrue((package / "schemas" / "per_atlas_map.schema.json").is_file())


if __name__ == "__main__":
    unittest.main()

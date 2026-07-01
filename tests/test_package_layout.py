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
        self.assertTrue((package / "prompts" / "03_generate_spritesheet.md").is_file())
        self.assertTrue((package / "prompts" / "04_verify_spritesheet.md").is_file())
        self.assertTrue((package / "scripts" / "build_spritesheet_prompt.py").is_file())
        self.assertTrue((package / "scripts" / "build_render_manifest.py").is_file())
        self.assertTrue((package / "scripts" / "data_io.py").is_file())


if __name__ == "__main__":
    unittest.main()

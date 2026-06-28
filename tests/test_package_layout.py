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


if __name__ == "__main__":
    unittest.main()

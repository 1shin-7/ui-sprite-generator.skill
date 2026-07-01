import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ui-sprite-generator" / "scripts" / "data_io.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("data_io_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DataIoTests(unittest.TestCase):
    def test_loads_json_without_yaml_dependency(self):
        module = load_script_module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.json"
            path.write_text(json.dumps({"name": "ok", "items": [1, 2]}), encoding="utf-8")

            self.assertEqual(module.load_data(path), {"name": "ok", "items": [1, 2]})

    def test_yaml_without_pyyaml_has_clear_error(self):
        module = load_script_module()
        if module.yaml is not None:
            self.skipTest("PyYAML is installed in this environment")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.yaml"
            path.write_text("name: ok\n", encoding="utf-8")

            with self.assertRaisesRegex(module.DataIOError, "PyYAML is required"):
                module.load_data(path)

    def test_rejects_unknown_extension(self):
        module = load_script_module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.txt"
            path.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(module.DataIOError, "unsupported data file extension"):
                module.load_data(path)


if __name__ == "__main__":
    unittest.main()

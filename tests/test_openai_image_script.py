import os
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ui-sprite-generator" / "scripts" / "openai_image.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("openai_image_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OpenAIImageScriptTests(unittest.TestCase):
    def test_help_does_not_expose_api_key_argument(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--env-file", result.stdout)
        self.assertIn("--run-dir", result.stdout)
        self.assertIn("--base-url", result.stdout)
        self.assertIn("--mode", result.stdout)
        self.assertIn("--spec", result.stdout)
        self.assertIn("--purpose", result.stdout)
        self.assertIn("--quality", result.stdout)
        self.assertIn("--response-format", result.stdout)
        self.assertIn("--normalize-background-to-source", result.stdout)
        self.assertNotIn("--api-key", result.stdout)

    def test_missing_api_key_fails_with_env_guidance(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            env_file = work / ".env"
            env_file.write_text("IMAGE_API_BASE_URL=https://example.test/v1/images/generations\n", encoding="utf-8")
            prompt = work / "prompt.txt"
            prompt.write_text("Generate a UI atlas.", encoding="utf-8")

            env = os.environ.copy()
            env.pop("IMAGE_API_KEY", None)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--env-file",
                    str(env_file),
                    "--prompt-file",
                    str(prompt),
                    "--output",
                    str(work / "out.png"),
                ],
                text=True,
                capture_output=True,
                env=env,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("IMAGE_API_KEY", result.stderr)
            self.assertIn("environment", result.stderr.lower())

    def test_generation_payload_includes_quality_and_response_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            prompt = work / "prompt.txt"
            prompt.write_text("Generate a UI atlas.", encoding="utf-8")
            module = load_script_module()
            args = module.parse_args(
                [
                    "--prompt-file",
                    str(prompt),
                    "--output",
                    str(work / "out.png"),
                    "--model",
                    "gpt-image-2",
                    "--size",
                    "1536x1024",
                    "--quality",
                    "high",
                    "--response-format",
                    "b64_json",
                ]
            )

            payload = module.build_json_payload(args, {})

            self.assertEqual(payload["model"], "gpt-image-2")
            self.assertEqual(payload["quality"], "high")
            self.assertEqual(payload["response_format"], "b64_json")
            self.assertNotIn("image", payload)

    def test_base_url_argument_overrides_env_file(self):
        module = load_script_module()
        args = module.parse_args(
            [
                "--base-url",
                "https://example.test/v1/images/edits",
                "--prompt-file",
                "prompt.txt",
                "--output",
                "out.png",
            ]
        )

        self.assertEqual(
            module.resolve_base_url(args, {"IMAGE_API_BASE_URL": "https://wrong.test/v1/images/generations"}),
            "https://example.test/v1/images/edits",
        )

    def test_run_dir_loads_shared_env_and_run_local_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            run_root = work / "ui-sprite-runs"
            run_dir = run_root / "2026-06-28-panel"
            run_dir.mkdir(parents=True)
            (run_root / ".env").write_text(
                "\n".join(
                    [
                        "IMAGE_API_BASE_URL=https://example.test/v1/images/generations",
                        "IMAGE_API_KEY=shared-key",
                        "IMAGE_API_MODEL=shared-model",
                        "IMAGE_API_SIZE=1536x1024",
                    ]
                ),
                encoding="utf-8",
            )
            (run_dir / ".env").write_text(
                "\n".join(
                    [
                        "IMAGE_API_MODEL=run-model",
                        "IMAGE_API_QUALITY=high",
                    ]
                ),
                encoding="utf-8",
            )
            module = load_script_module()
            args = module.parse_args(
                [
                    "--run-dir",
                    str(run_dir),
                    "--prompt-file",
                    "prompt.txt",
                    "--output",
                    "out.png",
                ]
            )

            values = module.load_env_values(args)

            self.assertEqual(values["IMAGE_API_BASE_URL"], "https://example.test/v1/images/generations")
            self.assertEqual(values["IMAGE_API_KEY"], "shared-key")
            self.assertEqual(values["IMAGE_API_MODEL"], "run-model")
            self.assertEqual(values["IMAGE_API_SIZE"], "1536x1024")
            self.assertEqual(values["IMAGE_API_QUALITY"], "high")

    def test_run_dir_allows_missing_run_local_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            run_root = work / "ui-sprite-runs"
            run_dir = run_root / "2026-06-28-panel"
            run_dir.mkdir(parents=True)
            (run_root / ".env").write_text(
                "IMAGE_API_KEY=shared-key\nIMAGE_API_MODEL=shared-model\n",
                encoding="utf-8",
            )
            module = load_script_module()
            args = module.parse_args(
                [
                    "--run-dir",
                    str(run_dir),
                    "--prompt-file",
                    "prompt.txt",
                    "--output",
                    "out.png",
                ]
            )

            values = module.load_env_values(args)

            self.assertEqual(values["IMAGE_API_KEY"], "shared-key")
            self.assertEqual(values["IMAGE_API_MODEL"], "shared-model")

    def test_edit_multipart_supports_repeated_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            prompt = work / "prompt.txt"
            prompt.write_text("Redraw the UI sprites.", encoding="utf-8")
            first = work / "reference.png"
            first.write_bytes(b"png-bytes")
            second = work / "mask.jpg"
            second.write_bytes(b"jpg-bytes")
            module = load_script_module()
            args = module.parse_args(
                [
                    "--mode",
                    "edits",
                    "--prompt-file",
                    str(prompt),
                    "--output",
                    str(work / "out.png"),
                    "--input-image",
                    str(first),
                    "--input-image",
                    str(second),
                    "--model",
                    "gpt-image-2",
                    "--size",
                    "1536x1024",
                    "--quality",
                    "high",
                    "--response-format",
                    "b64_json",
                ]
            )

            body, content_type = module.build_multipart_body(args, {}, boundary="BOUNDARY")

            body_text = body.decode("latin-1")
            self.assertIn("multipart/form-data; boundary=BOUNDARY", content_type)
            self.assertEqual(body_text.count('name="image";'), 2)
            self.assertIn('name="quality"', body_text)
            self.assertIn("\r\nhigh\r\n", body_text)
            self.assertIn('name="response_format"', body_text)
            self.assertIn("\r\nb64_json\r\n", body_text)
            self.assertNotIn("Bearer", body_text)

    def test_auto_background_size_uses_source_aspect_without_exact_source_dimensions(self):
        module = load_script_module()
        spec = {"source_image": {"path": "effect.png", "width": 848, "height": 790}}
        args = module.parse_args(
            [
                "--purpose",
                "background",
                "--size",
                "auto",
                "--prompt-file",
                "prompt.txt",
                "--output",
                "out.png",
            ]
        )

        size = module.resolve_size(args, {}, spec=spec)

        self.assertEqual(size, "1024x1024")

    def test_auto_background_size_selects_orientation_by_cover_crop_cost(self):
        module = load_script_module()
        landscape = {"source_image": {"path": "effect.png", "width": 1600, "height": 900}}
        portrait = {"source_image": {"path": "effect.png", "width": 900, "height": 1600}}

        landscape_args = module.parse_args(
            [
                "--purpose",
                "background",
                "--size",
                "auto",
                "--prompt-file",
                "prompt.txt",
                "--output",
                "out.png",
            ]
        )
        portrait_args = module.parse_args(
            [
                "--purpose",
                "background",
                "--size",
                "auto",
                "--prompt-file",
                "prompt.txt",
                "--output",
                "out.png",
            ]
        )

        self.assertEqual(module.resolve_size(landscape_args, {}, spec=landscape), "1536x1024")
        self.assertEqual(module.resolve_size(portrait_args, {}, spec=portrait), "1024x1536")

    def test_explicit_size_overrides_auto_inputs(self):
        module = load_script_module()
        spec = {"source_image": {"path": "effect.png", "width": 900, "height": 1600}}
        args = module.parse_args(
            [
                "--purpose",
                "background",
                "--size",
                "2048x1024",
                "--prompt-file",
                "prompt.txt",
                "--output",
                "out.png",
            ]
        )

        self.assertEqual(module.resolve_size(args, {"IMAGE_API_SIZE": "auto"}, spec=spec), "2048x1024")

    def test_auto_atlas_size_is_not_forced_to_source_canvas_aspect(self):
        module = load_script_module()
        spec = {"source_image": {"path": "effect.png", "width": 300, "height": 1200}}
        args = module.parse_args(
            [
                "--purpose",
                "atlas",
                "--size",
                "auto",
                "--prompt-file",
                "prompt.txt",
                "--output",
                "out.png",
            ]
        )

        self.assertEqual(module.resolve_size(args, {}, spec=spec), "1536x1024")

    def test_auto_size_requires_spec_for_background(self):
        module = load_script_module()
        args = module.parse_args(
            [
                "--purpose",
                "background",
                "--size",
                "auto",
                "--prompt-file",
                "prompt.txt",
                "--output",
                "out.png",
            ]
        )

        with self.assertRaisesRegex(module.ImageAPIError, "--spec"):
            module.resolve_size(args, {}, spec=None)

    def test_background_normalization_cover_crops_to_source_dimensions(self):
        module = load_script_module()
        spec = {"source_image": {"path": "effect.png", "width": 848, "height": 790}}

        fake_image = mock.Mock()
        fake_image.size = (1536, 1024)
        fake_image.crop.return_value = fake_image
        fake_image.resize.return_value = fake_image
        fake_image.convert.return_value = fake_image

        with mock.patch.object(module.Image, "open") as image_open:
            image_open.return_value.__enter__.return_value = fake_image
            module.normalize_background_to_source("generated.png", spec)

        fake_image.crop.assert_called_once_with((218, 0, 1317, 1024))
        fake_image.resize.assert_called_once_with((848, 790), module.Image.Resampling.LANCZOS)
        fake_image.save.assert_called_once_with("generated.png")


if __name__ == "__main__":
    unittest.main()

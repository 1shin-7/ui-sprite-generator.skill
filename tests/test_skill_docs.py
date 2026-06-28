from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillDocTests(unittest.TestCase):
    def test_external_image_generation_fallback_mentions_security_boundaries(self):
        content = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()

        self.assertIn("external image generation fallback", content)
        self.assertIn("base url", content)
        self.assertIn("api key", content)
        self.assertIn("token", content)
        self.assertIn("environment variable", content)
        self.assertIn("never write", content)
        self.assertIn("large images", content)
        self.assertIn("thumbnail", content)

    def test_atlas_prompt_forbids_crop_fallback_and_requires_redrawn_sprites(self):
        content = (ROOT / "ui-sprite-generator" / "prompts" / "03_generate_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("do not crop", content)
        self.assertIn("pillow", content)
        self.assertIn("redraw", content)
        self.assertIn("isolated sprite", content)
        self.assertIn("border decoration", content)
        self.assertIn("glow", content)
        self.assertIn("hollow", content)
        self.assertIn("bar_fill_texture", content)
        self.assertIn("rich texture", content)

    def test_external_generation_fallback_forbids_local_substitution_for_mandatory_generation_steps(self):
        content = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()

        self.assertIn("phase 2 and phase 3 are mandatory generation steps", content)
        self.assertIn("do not substitute local pillow", content)
        self.assertIn("scripts/openai_image.py", content)
        self.assertIn("config/image-api.env.example", content)
        self.assertIn("create a shared `ui-sprite-runs/.env`", content)
        self.assertIn("do not paste api keys into prompts", content)
        self.assertIn("timeout", content)
        self.assertIn("response status", content)
        self.assertIn("multipart", content)
        self.assertIn("repeated `--input-image`", content)
        self.assertIn("image_api_quality", content)
        self.assertIn("image_api_response_format", content)

    def test_skill_rejects_token_saving_crop_rationalizations(self):
        content = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()

        self.assertIn("token-saving shortcut", content)
        self.assertIn("usable result", content)
        self.assertIn("deterministic component slicing", content)
        self.assertIn("absolute-positioned html reconstruction from crops", content)
        self.assertIn("analysis reference only", content)
        self.assertIn("not formal atlas art", content)

    def test_skill_defines_generation_capability_gate_and_shared_env(self):
        content = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()

        self.assertIn("generation capability gate", content)
        self.assertIn("only generative image services count", content)
        self.assertIn("do not check local image-processing tools as substitutes", content)
        self.assertIn("pillow/opencv/canvas/crop are reference preparation only", content)
        self.assertIn("if no generative service is available, stop and configure the external image api", content)
        self.assertIn("ui-sprite-runs/.env", content)
        self.assertIn("ui-sprite-runs/.gitignore", content)
        self.assertIn("do not ask the user to edit a non-existent .env path", content)

    def test_run_root_gitignore_template_ignores_shared_env(self):
        content = (ROOT / "ui-sprite-generator" / "templates" / "runs.gitignore").read_text(encoding="utf-8")

        self.assertIn(".env", content)
        self.assertIn(".env.*", content)
        self.assertIn("*.env", content)

    def test_background_prompt_forbids_whole_image_background_plate_shortcut(self):
        content = (ROOT / "ui-sprite-generator" / "prompts" / "02_generate_background_plate.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("do not use the whole effect image as the background plate", content)
        self.assertIn("do not preserve foreground ui chrome", content)
        self.assertIn("remove foreground ui first", content)
        self.assertIn("inpaint or regenerate", content)
        self.assertIn("stop and ask for an image-generation service", content)

    def test_atlas_prompt_rejects_rectangular_cutout_assets(self):
        content = (ROOT / "ui-sprite-generator" / "prompts" / "03_generate_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("token-saving shortcut", content)
        self.assertIn("deterministic slicing", content)
        self.assertIn("absolute-positioned html reconstruction from crops", content)
        self.assertIn("dirty rectangular cutout", content)
        self.assertIn("source background pixels visible", content)
        self.assertIn("clipped ornament", content)
        self.assertIn("regenerate the sprite", content)

    def test_phase_3_requires_builder_not_handwritten_prompt(self):
        skill = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()
        atlas_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "03_generate_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("scripts/build_atlas_prompt.py", skill)
        self.assertIn("ui_atlas.md", skill)
        self.assertIn("do not handwrite", skill)
        self.assertIn("do not summarize", skill)
        self.assertIn("must be generated by `scripts/build_atlas_prompt.py`", atlas_prompt)
        self.assertIn("do not rewrite this prompt into a shorter prompt", atlas_prompt)

    def test_atlas_prompt_has_generic_center_semantics(self):
        content = (ROOT / "ui-sprite-generator" / "prompts" / "03_generate_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("hollow or transparent centers must remain empty", content)
        self.assertIn("no interior content", content)
        self.assertIn("no illustrative fill", content)
        self.assertIn("style words affect only allowed component surfaces", content)
        self.assertNotIn("xianxia", content)
        self.assertNotIn("mountain", content)
        self.assertNotIn("cloud pattern", content)

    def test_atlas_qa_gate_exists(self):
        content = (ROOT / "ui-sprite-generator" / "prompts" / "04_verify_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("invented_internal_texture", content)
        self.assertIn("center_correct", content)
        self.assertIn("decoration_missing", content)
        self.assertIn("source_background_pixels", content)
        self.assertIn("clipped_ornament", content)
        self.assertIn("flat_bar_fill", content)

    def test_runtime_image_size_policy_does_not_create_stable_plan_json(self):
        skill = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()
        background_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "02_generate_background_plate.md").read_text(
            encoding="utf-8"
        ).lower()
        atlas_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "03_generate_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("--size auto", skill)
        self.assertIn("--purpose background", skill)
        self.assertIn("--purpose atlas", skill)
        self.assertIn("--normalize-background-to-source", skill)
        self.assertIn("api generation size", background_prompt)
        self.assertIn("final background_plate.png", background_prompt)
        self.assertIn("canvas size is a generation preference", atlas_prompt)
        self.assertIn("not the source image dimensions", atlas_prompt)
        self.assertNotIn("image_size_plan.json", skill)
        self.assertIn("do not promote `sheet_plan.json`", skill)


if __name__ == "__main__":
    unittest.main()

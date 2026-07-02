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

    def test_generation_gate_prefers_native_image_tools_before_helper_fallback(self):
        content = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()

        self.assertIn("check native image-generation tools first", content)
        self.assertIn("codex desktop", content)
        self.assertIn("image_gen", content)
        self.assertIn("do not ask for external image api configuration", content)
        self.assertIn("scripts/openai_image.py is the fallback", content)
        self.assertIn("only when no native generative tool is available", content)

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

    def test_phase_3_requires_single_strict_atlas_builder(self):
        skill = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()
        atlas_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "03_generate_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("scripts/build_atlas_prompt.py", skill)
        self.assertIn("atlas/<name>.prompt.md", skill)
        self.assertIn("labeled atlas", skill)
        self.assertIn("do not handwrite", skill)
        self.assertIn("do not summarize", skill)
        self.assertIn("must be generated by `scripts/build_atlas_prompt.py`", atlas_prompt)
        self.assertIn("--atlas-bg chroma-key", atlas_prompt)
        self.assertIn("--atlas-key-color #00ff00", atlas_prompt)
        self.assertIn("chroma-key", skill)
        self.assertIn("transparentize-border", skill)
        self.assertIn("--atlas-bg transparent", atlas_prompt)
        self.assertIn("--layout-strategy maxrects", atlas_prompt)
        self.assertIn("--layout-strategy area-budget", atlas_prompt)
        self.assertIn("label height", atlas_prompt)
        self.assertIn("label gap", atlas_prompt)
        self.assertIn("maxrects", atlas_prompt)
        self.assertIn("external label", atlas_prompt)
        self.assertIn("debug_bbox.png", skill)
        self.assertNotIn("build_spritesheet_prompt.py", skill)
        self.assertNotIn("03_generate_spritesheet.md", skill)
        self.assertNotIn("04_verify_spritesheet.md", skill)
        self.assertNotIn("deprecated guard", skill)

    def test_atlas_prompt_has_generic_center_surface_and_occlusion_semantics(self):
        content = (ROOT / "ui-sprite-generator" / "prompts" / "03_generate_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("hollow or transparent centers must remain empty", content)
        self.assertIn("no interior content", content)
        self.assertIn("no illustrative fill", content)
        self.assertIn("style words affect only allowed component surfaces", content)
        self.assertIn("flat_fill", content)
        self.assertIn("do not add painterly texture", content)
        self.assertIn("occlusion", content)
        self.assertIn("complete unobstructed sprite", content)
        self.assertNotIn("xianxia", content)
        self.assertNotIn("mountain", content)
        self.assertNotIn("cloud pattern", content)

    def test_atlas_qa_gate_exists(self):
        content = (ROOT / "ui-sprite-generator" / "prompts" / "04_verify_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("atlas/<name>.prompt.md", content)
        self.assertIn("local atlas spec json", content)
        self.assertNotIn("`spec.yaml`, one generated", content)
        self.assertIn("unwanted_texture_noise", content)
        self.assertIn("flat_fill_pollution", content)
        self.assertIn("occlusion_contamination", content)
        self.assertIn("label_inside_sprite", content)
        self.assertIn("center_correct", content)
        self.assertIn("decoration_missing", content)
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
        self.assertIn("--normalize-background-to-source", skill)
        self.assertIn("api generation size", background_prompt)
        self.assertIn("final background_plate.png", background_prompt)
        self.assertIn("canvas size is a generation preference", atlas_prompt)
        self.assertIn("not the source image dimensions", atlas_prompt)
        self.assertNotIn("image_size_plan.json", skill)
        self.assertNotIn("image_size_plan.yaml", skill)
        self.assertIn("do not promote `sheet_plan.yaml`", skill)

    def test_phase_4_documents_optional_maxrects_layout_planner(self):
        skill = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()

        self.assertIn("scripts/plan_atlas_layout.py", skill)
        self.assertIn("maxrects", skill)
        self.assertIn("--layout-strategy maxrects", skill)
        self.assertIn("--layout-strategy area-budget", skill)
        self.assertIn("default", skill)
        self.assertIn("chroma-key", skill)
        self.assertIn("not a stable contract", skill)

    def test_skill_requires_progressive_prompt_reading(self):
        skill = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()

        self.assertIn("progressive reading", skill)
        self.assertIn("read only the prompt for the current phase", skill)
        self.assertIn("after completing a phase", skill)
        self.assertIn("do not preload every prompt", skill)
        self.assertIn("do not preload script source", skill)

    def test_spec_prompt_allows_overlapping_source_bboxes_and_occlusion_reconstruction(self):
        content = (ROOT / "ui-sprite-generator" / "prompts" / "01_extract_spec.md").read_text(
            encoding="utf-8"
        ).lower()
        schema = (ROOT / "ui-sprite-generator" / "schemas" / "spec.schema.json").read_text(encoding="utf-8").lower()

        self.assertIn("source_bbox values may overlap", content)
        self.assertIn("do not shift", content)
        self.assertIn("instances[]", content)
        self.assertIn("occlusion", content)
        self.assertIn("surface_policy", content)
        self.assertIn('"1.2"', schema)
        self.assertIn('"instances"', schema)
        self.assertIn("ui_style", schema)
        self.assertIn("background_style", schema)
        self.assertIn("surface_policy", schema)
        self.assertIn("occlusion", schema)

    def test_spec_prompt_requires_conservative_exact_component_reuse(self):
        extract_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "01_extract_spec.md").read_text(
            encoding="utf-8"
        ).lower()
        verify_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "02_verify_spec.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("merge only exact reusable sprite definitions", extract_prompt)
        self.assertIn("do not merge near-duplicates", extract_prompt)
        self.assertIn("when uncertain", extract_prompt)
        self.assertIn("multiple lightweight `instances[]` entries", extract_prompt)
        self.assertIn("merge component definitions only when they are visually identical", verify_prompt)
        self.assertIn("when uncertain, keep separate", verify_prompt)

    def test_resolution_and_bar_contracts_prevent_overgeneration(self):
        spec_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "01_extract_spec.md").read_text(
            encoding="utf-8"
        ).lower()
        atlas_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "03_generate_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()
        qa_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "04_verify_ui_atlas.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("icon", spec_prompt)
        self.assertIn("max 2x", spec_prompt)
        self.assertIn("never solve packing by increasing target_px", spec_prompt)
        self.assertIn("bar_fill_texture", spec_prompt)
        self.assertIn("rectangular full-width fill texture", spec_prompt)
        self.assertIn("do not infer an irregular visible silhouette", spec_prompt)
        self.assertIn("do not increase target_px", atlas_prompt)
        self.assertIn("do not invent detail", atlas_prompt)
        self.assertIn("do not infer missing ornament", atlas_prompt)
        self.assertIn("when uncertain", atlas_prompt)
        self.assertIn("full rectangular fill texture", atlas_prompt)
        self.assertIn("overgenerated_detail", qa_prompt)
        self.assertIn("non_rectangular_bar_fill", qa_prompt)

    def test_yaml_render_manifest_contracts_are_documented(self):
        skill = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()
        atlas_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "04_extract_atlas_map.md").read_text(
            encoding="utf-8"
        ).lower()
        html_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "05_generate_playwright_html.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("spec.yaml", skill)
        self.assertIn("render.yaml", skill)
        self.assertIn("spec.yaml is authoritative", skill)
        self.assertIn("`instances[]` are authoritative", skill)
        self.assertIn("per-atlas crop contract", skill)
        self.assertIn("phase 4", skill)
        self.assertIn("local atlas contract", skill)
        self.assertIn("not the full `spec.yaml`", skill)
        self.assertIn("build_render_manifest.py", skill)
        self.assertIn("do not infer, copy, or emit final layout fields", atlas_prompt)
        self.assertIn("atlas/<name>.prompt.md", atlas_prompt)
        self.assertIn("local atlas spec json", atlas_prompt)
        self.assertNotIn("**inputs:** `spec.yaml`", atlas_prompt)
        self.assertIn("source_bbox", atlas_prompt)
        self.assertIn("z_index", atlas_prompt)
        self.assertIn("render.yaml", html_prompt)
        self.assertIn("render.root_size", html_prompt)

    def test_flat_session_and_per_atlas_maps_are_documented(self):
        skill = (ROOT / "ui-sprite-generator" / "SKILL.md").read_text(encoding="utf-8").lower()
        atlas_prompt = (ROOT / "ui-sprite-generator" / "prompts" / "04_extract_atlas_map.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("effect.png", skill)
        self.assertIn("atlas/*.map.yaml", skill)
        self.assertIn("sprites/", skill)
        self.assertIn("per-atlas crop contract", skill)
        self.assertIn("legacy input", skill)
        self.assertIn("--atlas-dir", skill)
        self.assertIn("one generated atlas image", atlas_prompt)
        self.assertIn("output only one per-atlas yaml object", atlas_prompt)
        self.assertIn("do not output a global atlas_map.yaml", atlas_prompt)


if __name__ == "__main__":
    unittest.main()

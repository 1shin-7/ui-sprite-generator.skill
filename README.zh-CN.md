# ui-sprite-generator.skill

<p align="center">
  <img src="https://socialify.git.ci/1shin-7/ui-sprite-generator.skill/image?description=1&font=Inter&forks=1&issues=1&language=1&name=1&owner=1&pattern=Signal&pulls=1&stargazers=1&theme=Auto" alt="ui-sprite-generator social preview" />
</p>

<p align="center">
  <a href="https://github.com/1shin-7/ui-sprite-generator.skill">
    <img alt="GitHub repo" src="https://img.shields.io/badge/GitHub-ui--sprite--generator.skill-181717?style=for-the-badge&logo=github" />
  </a>
  <img alt="Skill" src="https://img.shields.io/badge/Codex-Skill-10A37F?style=for-the-badge&logo=openai&logoColor=white" />
  <img alt="Docs language" src="https://img.shields.io/badge/Docs-CN%20%7C%20EN-2563EB?style=for-the-badge" />
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
</p>

<p align="center">
  <a href="./README.md">English</a> |
  <a href="./README.zh-CN.md">简体中文</a>
</p>

> 将游戏 UI 效果图拆解为干净背景、重绘式 labeled spritesheet、切图资产和可被 Playwright 验证的静态 HTML。

`ui-sprite-generator.skill` 是一个 Codex skill，用于把游戏 UI 效果图转换为可被 Playwright 截图验证的静态重建产物：干净背景板、重新绘制的 labeled spritesheet、切出的 sprite PNG，以及最终 HTML。

它的目标不是把截图矩形裁开，而是把复杂 UI chrome 还原为可验证、可切图、可复用的资产管线。

## Features

- 将 UI 效果图拆成语义资产，而不是直接裁出带背景污染的矩形块。
- 生成 `spec.yaml`：记录 source bbox、组件角色、遮挡关系、surface policy、分辨率策略和渲染模式。
- 生成 `background_plate.png`：移除前景 UI，并尽可能重建被 UI 遮挡的背景区域。
- 默认使用 labeled spritesheet：每个 sprite 外部带 id label，便于人工和模型在切图前做 QA。
- `scripts/ui_slice.py` 只做机械切图和边缘背景清理，不负责猜测、确认或修正坐标。
- `scripts/openai_image.py` 支持 OpenAI-compatible `/images/generations` 与 `/images/edits`。
- 输出面向 Playwright 的静态 HTML，包含 `window.__UI_READY__ = true` 和可选 debug overlay。

## Quickstart

安装 skill：

```bash
pnpx skills add https://github.com/1shin-7/ui-sprite-generator.skill --skill ui-sprite-generator
```

## Concept

工作流按职责拆分：

1. `spec.yaml` 描述效果图里的 UI 语义。
2. `background_plate.png` 还原 UI 背后的干净背景。
3. Labeled spritesheet 重新绘制隔离 UI 组件，并把 id label 放在 sprite 外部。
4. `atlas_map.yaml` 记录 QA 后的 crop 坐标和输出文件名。
5. `render.yaml` 合并 spec 中的布局和 atlas map 中的 sprite 文件名。
6. `ui_slice.py` 只按坐标切图，不修图、不猜图、不生成报告。
7. `html/index.html` 用背景板和绝对定位 sprite 重建场景，供 Playwright 截图。

默认路线是 labeled spritesheet，而不是直接生成正式 atlas。原因很简单：label 能让失败变得可观察。比如装饰缺失、flat fill 被污染、遮挡物混入、label 压进 sprite、模型脑补过多细节、进度条填充向内坍缩，这些问题都应该在切图前暴露。

进度条填充、hollow frame、被文字或装饰遮挡的组件尤其不能直接矩形裁切。正式 sprite 应该按照 spec 中的语义重绘，HTML 再负责裁剪、叠放和显示比例。

## Dev

聚焦测试：

```bash
python -B -m unittest tests.test_build_spritesheet_prompt
python -B -m unittest tests.test_openai_image_script
python -B -m unittest tests.test_ui_slice
```

完整本地验证：

```bash
python -B -m unittest tests.test_skill_docs tests.test_build_spritesheet_prompt tests.test_build_atlas_prompt tests.test_openai_image_script tests.test_ui_slice tests.test_package_layout
python -m py_compile ui-sprite-generator/scripts/openai_image.py ui-sprite-generator/scripts/build_atlas_prompt.py ui-sprite-generator/scripts/build_spritesheet_prompt.py ui-sprite-generator/scripts/ui_slice.py
git diff --check
```

仓库结构：

```text
ui-sprite-generator/
  SKILL.md
  prompts/
  schemas/
  scripts/
  templates/
tests/
```

开发时不要把 `ui_sprite_skill/` 当作正式包路径；正式 skill 包位于 `ui-sprite-generator/`。

# AI Short Drama From Zero Roadmap

[简体中文](README.md) | [English](README_EN.md)

This roadmap describes likely directions, not guaranteed delivery dates. Priorities are based on reproducible creator problems, downstream impact, and community feedback.

## Status legend

- ✅ Shipped
- 🟡 Planned
- 🔎 Researching
- 💬 Community input wanted

## V2.0 — Production diagnosis and repair ✅

- Project-stage diagnosis with evidence.
- Completed, incomplete, blocked, and rework reporting.
- At least three concrete next actions with a recommendation.
- Novel adaptation, dialogue, production slicing, shot scripts, and storyboard prompts.
- Character, costume, crowd, scene, prop, and voice asset workflows.
- Seedance 2.0 multimodal prompts with explicit `@image`, `@video`, and `@audio` reference roles.
- Reference-role control, clean context reset, and source-drift checks.
- Generation-attempt logging and stop conditions.
- Voice repair, clip stitching, and final-film QC.
- Four validators for timeline, project state, prompt packages, and continuity.
- Chinese and English project documentation.
- Original workflow demo, comparison visual, and structured issue templates.

## V2.1 — Step-by-step beginner mode ✅

- Three automatic entry points: idea only, existing writing, or a half-finished project.
- One active production gate at a time instead of a full workflow dump.
- Plain-language terminology and recommended, reversible defaults.
- Beginner progress card with completed, locked, missing, blocked, and rework items.
- Mobile-friendly instructions and one-letter next-step selection.
- Acceptance criteria for every gate from premise to final-film QC.
- Tutorial snapshots with preserved creator attribution.

## V2.2 — Duration choice gate and project cover ✅

- Mandatory user choice between 10-second and 15-second production slicing.
- Optional side-by-side sample before the user locks a mode.
- Project-state persistence and validation for the selected duration mode.
- One duration mode per episode or batch unless the user explicitly changes it.
- New bilingual GitHub social preview and README cover.

## V2.3 — Fixed output and choice contract ✅

- One four-part response shell: result, progress update, self-check, and next-step choice.
- Exactly three A/B/C actions after every response, with exactly one recommendation.
- Stable production-document wrapper and reusable template.
- Compact shot metadata, asset continuity, and timecode execution tables.
- Clear distinction between a 10s/15s production unit and its internal camera shots.
- Required dialogue/audio, opening and final states, next-unit inheritance, and per-unit QC.

## V2.4 — Tool-aware image workflows ✅

- GPT professional 3×3 cinematic storyboard workboards.
- Gemini simplified 3×3 storyboard prompts.
- Overhead and front blocking images for other generators.
- Named character master-board and character-sheet prompts.

## V2.5 — Seedance 2.0 single-format export ✅

- One clean Seedance 2.0 natural-language prompt for every video production unit.
- Actual uploaded media referenced through uniquely assigned `@image`, `@video`, and `@audio` roles.
- No I2V, FLF2V, WAN, VACE, first/last-frame fields, `CUT`, `TAIL`, XML, or alternate platform exports.
- A reusable Seedance 2.0 prompt template and production validation rules.
- Fixed UTF-8 CSV exports for shootable screenplays and complete shot scripts.

## V2.6 — Reproducible example packs 🟡

- A complete original sample from premise to final prompt package.
- Small examples for prop drift, blocking errors, dialogue overload, and reference conflicts.
- Validator fixtures with known-pass and known-fail cases.
- Machine-readable JSON Schema files for the current validation inputs.
- More before/after repair reports that never contain private project material.

## V2.7 — Media review and continuity tools 🔎

- Structured image and video review checklists.
- Clip-boundary comparison records for action completion, motion, prop, wardrobe, and audio state.
- Episode-level defect summaries and repair priority scores.
- Optional utilities for generating review contact sheets from user-authorized media.

## V3.0 — Portable production state 💬

- A portable project-state package that can move between sessions and collaborators.
- Stable IDs for scenes, characters, costumes, props, voices, shots, references, and generation attempts.
- Change-impact mapping from a source asset to every dependent production document.
- Human-readable reports generated from the same machine-readable state.

## How to influence the roadmap

Open an issue using the most relevant template:

- **Generation / prompt failure** for repeatable model or reference problems.
- **Bug report** for incorrect Skill behavior, validation, or documentation.
- **Feature request** for a reusable workflow improvement.

Please remove private information, use only media you own or are authorized to share, and include the smallest reproducible example possible.

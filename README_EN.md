# AI Short Drama From Zero

[简体中文](README.md) | **English**

> A production-oriented Skill that takes an AI short drama from an idea or novel through adaptation, dialogue, audiovisual beats, locked assets, spatially solved camera plans, storyboards, video prompts, QA, audio repair, editing, and final delivery.

![Version](https://img.shields.io/badge/version-2.4.0-2563eb)
![License](https://img.shields.io/badge/license-MIT-16a34a)

The invocation name remains:

```text
$ai-short-drama-director
```

## What changed in V2.4

The Skill no longer treats a locked camera, camera movement, and CUT as three separate upstream choices.

It now uses one unified directorial camera program:

```text
idea or novel
→ adaptation and shootable script
→ dialogue, action chain, and audiovisual beats
→ lock visual, character, prop, and scene-layout assets
→ 04A base scene-space model
→ 15 unified directorial camera plan: how to shoot, how the camera travels, and where to CUT
→ 04B actor and camera XYZ trajectory solve
→ return to 15 when the spatial solve is impossible
→ 14 shot-task and action-coverage validation
→ 13 CUT-geometry audit
→ SEG packaging, storyboard, and video prompt
```

Inside one SHOT, camera state `C(t)` is continuous. When it remains unchanged, the result is a locked camera. When it changes continuously, the result is camera movement. A boundary between two continuous SHOT intervals is a CUT. These are outcomes of one plan, not three independent calculation systems.

The Skill supplies the professional primary proposal when the project contains enough information. The user may request changes, but the workflow does not push the decision “locked, movement, or CUT?” back to the user.

## Main capabilities

- Turn an idea, story, or novel into a shootable short-drama structure.
- Preserve locked dialogue and project facts while converting narration into visible action.
- Lock character, costume, prop, voice, and scene-layout assets before camera calculation.
- Build a measurable scene basis with dimensions, anchors, walkable zones, obstacles, and relationship axes.
- Design SHOT intervals, camera-trajectory intent, endpoints, holds, and CUT intent in one director-authored plan.
- Solve the plan into actor and camera XYZ keyframes, world-facing vectors, speed, clearance, obstacle, and axis evidence.
- Return an infeasible solve to the directing layer instead of silently changing the scene purpose or asking the user to choose another camera mode.
- Validate action visibility, entry and exit boundaries, POV/OTS/INSERT evidence, state machines, and adjacent-SHOT geometry.
- Distinguish SEG, SHOT, CUT, camera movement, framing, and soft focal-feel hints.
- Support ordinary dialogue, high-speed action, and fixed-camera time-passage SEG types.
- Produce production documents, storyboards, Seedance 2.0/I2V/FLF2V prompts, repair reports, and final QA.

## Core rule sources

| Module | Rule source |
|---|---|
| Script, dialogue, timing, and SEG packaging | `references/01-script-slicing.md` |
| Visual style | `references/02-visual-style.md` |
| Character, prop, voice, and scene-layout assets | `references/03-asset-design.md` |
| 04A scene basis and 04B XYZ spatial solve | `references/04-blocking-continuity.md` |
| Video-prompt packaging | `references/05-video-prompting.md` |
| QA and repair | `references/06-qc-repair-post.md` |
| Storyboards and image prompts | `references/07-storyboard-image-prompts.md` |
| CUT geometry and adjacent-SHOT audit | `references/13-cut-shot-geometry.md` |
| SHOT task and action coverage | `references/14-shot-task-action-coverage.md` |
| Unified director-authored camera program | `references/15-directorial-camera-plan.md` |

`15-directorial-camera-plan.md` decides the intended photography and CUT semantics. `04-blocking-continuity.md` computes whether that plan is spatially executable. `14-shot-task-action-coverage.md` proves that the image actually covers the required task. `13-cut-shot-geometry.md` audits the proposed CUT; it does not invent a new CUT downstream.

## Validation tools

The repository includes ten dependency-free Python validators:

```bash
python3 scripts/validate_timeline.py timeline.json
python3 scripts/validate_segment_structure.py segment-structure.json
python3 scripts/validate_project_state.py project-state.json
python3 scripts/validate_prompt_package.py prompt-package.json
python3 scripts/validate_continuity.py continuity.json
python3 scripts/validate_directorial_camera_plan.py directorial-camera-plan.json
python3 scripts/validate_spatial_geometry.py spatial-geometry.json
python3 scripts/validate_shot_task.py shot-task.json
python3 scripts/validate_cut_geometry.py cut-geometry.json
python3 scripts/validate_rule_sources.py
```

`validate_directorial_camera_plan.py` accepts either a flat plan object or a wrapper named `directorial_camera_plan`. It derives fixed or moving behavior from XYZ keyframes; checks bounds, blocked volumes, actor and camera speeds, angular speed, dynamic camera-to-actor clearance, relationship-axis policy, full track coverage, and solved hold time; and reports whether the plan must return to the director for redesign.

`validate_segment_structure.py` continues to treat explicit SHOT boundaries as the only SHOT-count source. Framing changes, camera movement, or focal-feel changes do not automatically create a CUT.

## Quick start

Download the main branch ZIP or clone the repository:

```bash
git clone https://github.com/sanxsnr/ai-short-drama-from-zero.git
```

Keep `SKILL.md`, `references/`, `scripts/`, `assets/`, and `agents/` in their original relative locations when importing the Skill.

Example invocation:

```text
Use $ai-short-drama-director to inspect my current short-drama project, identify the real production stage and upstream cause of any error, repair the complete affected artifact, and report what is complete, in progress, blocked, or requires rework.
```

For a new project:

```text
Use $ai-short-drama-director to turn this novel into a shootable short drama. Build the dialogue and audiovisual action chain, lock the scene-layout assets, create a unified directorial camera plan, solve actor and camera XYZ trajectories, validate SHOT tasks and CUT geometry, then package production-ready SEGs.
```

## Repository structure

```text
ai-short-drama-from-zero/
├── SKILL.md
├── README.md
├── README_EN.md
├── agents/
├── assets/
├── references/
│   ├── 00-project-diagnosis.md
│   ├── 01-script-slicing.md
│   ├── 02-visual-style.md
│   ├── 03-asset-design.md
│   ├── 04-blocking-continuity.md
│   ├── 05-video-prompting.md
│   ├── 06-qc-repair-post.md
│   ├── 07-storyboard-image-prompts.md
│   ├── 08-document-revision-delivery.md
│   ├── 09-generation-session-control.md
│   ├── 10-voice-editing-repair.md
│   ├── 11-beginner-guided-mode.md
│   ├── 12-output-format-and-choice-footer.md
│   ├── 13-cut-shot-geometry.md
│   ├── 14-shot-task-action-coverage.md
│   └── 15-directorial-camera-plan.md
├── scripts/
│   ├── validate_timeline.py
│   ├── validate_segment_structure.py
│   ├── validate_project_state.py
│   ├── validate_prompt_package.py
│   ├── validate_continuity.py
│   ├── validate_directorial_camera_plan.py
│   ├── validate_spatial_geometry.py
│   ├── validate_shot_task.py
│   ├── validate_cut_geometry.py
│   └── validate_rule_sources.py
└── tests/
```

## Design boundaries

- Locked user facts and dialogue remain higher priority than generic rules.
- The spatial layer may reject a plan but may not silently redesign the director’s intention.
- The task layer may reject missing evidence but may not create a new SHOT boundary.
- The CUT layer audits the director’s CUT type, transition mechanism, action progress, axis, and visual difference; it does not add an unplanned CUT.
- Exact focal-length values remain optional visual hints, not hard spatial controls.
- High-speed-action exceptions do not apply to ordinary dialogue or routine prop actions.
- A visible day/night transition in one locked composition is not automatically a montage of different camera positions.
- The system reduces detectable structural errors but does not promise model approval or a perfect first generation.

## License

[MIT License](LICENSE)

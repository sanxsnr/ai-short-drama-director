# Third-Party Method References

This project independently re-expresses selected camera-direction ideas after reviewing the following MIT-licensed projects. No external Skill is installed as a runtime dependency, and their text is not copied wholesale into this project.

## Emily2040 / seedance-2.0

- Repository: `https://github.com/Emily2040/seedance-2.0`
- Reviewed files:
  - `skills/seedance-camera/SKILL.md`
  - `references/directing-engine.md`
- License: MIT
- Method ideas reviewed:
  - derive craft choices from one dramatic intention;
  - define a camera move with a start frame, movement, speed, subject relationship and endpoint;
  - use one primary camera idea per short clip;
  - treat camera movement as an audience-position and empathy decision rather than decorative vocabulary.

## MapleShaw / seedance2.0-prompt-skill

- Repository: `https://github.com/MapleShaw/seedance2.0-prompt-skill`
- Reviewed file:
  - `references/camera-codec.md`
- License: MIT
- Method ideas reviewed:
  - describe camera state through distance, height and azimuth dimensions;
  - model movement as those dimensions changing over time;
  - detect conflicting multi-axis movement;
  - separate spatial camera state from optical or lens-feel hints.

## Project-specific redesign

The adopted rules are rewritten for this project's AI-direct SEG/SHOT/CUT workflow and integrated with its existing world-coordinate, 180-degree-axis, action-state, task-coverage and CUT-geometry validators. Exact focal-length numbers remain soft visual hints in this project and are not restored as hard spatial controls.

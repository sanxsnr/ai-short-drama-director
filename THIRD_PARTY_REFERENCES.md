# Third-Party Method References

This repository independently re-expresses selected directing and camera-encoding ideas after reviewing the following MIT-licensed projects. No external Skill is installed as a runtime dependency, and their text is not copied wholesale.

## Emily2040 / seedance-2.0

- Repository: `https://github.com/Emily2040/seedance-2.0`
- Reviewed files:
  - `references/directing-engine.md`
  - `skills/seedance-camera/SKILL.md`
- License: MIT
- Method ideas reviewed:
  - the directing layer decides what a scene must do to the audience before choosing craft;
  - camera movement, framing, blocking, performance, sound, and CUT duration must serve one coherent scene intention;
  - a camera phrase should define a start frame, movement, speed, subject relationship, and endpoint;
  - the director, rather than the user, should provide the primary professional camera proposal when enough information exists.

## MapleShaw / seedance2.0-prompt-skill

- Repository: `https://github.com/MapleShaw/seedance2.0-prompt-skill`
- Reviewed file:
  - `references/camera-codec.md`
- License: MIT
- Method ideas reviewed:
  - represent camera state with distance, height, azimuth, and optical feel;
  - treat camera movement as camera coordinates changing through time;
  - detect excessive or contradictory multi-axis movement;
  - separate physical camera position from focal-length or lens-feel hints.

## Project-specific redesign

The adopted system is not a copy of either external project. This repository unifies fixed framing, camera movement, and CUTs in one time-ordered directorial camera plan:

1. the directing layer decides how the scene is photographed, how the camera travels inside each SHOT, and where SHOT boundaries occur;
2. the spatial layer solves the plan into actor and camera XYZ keyframes, world-facing vectors, obstacles, axis side, and visibility;
3. an infeasible spatial solve returns to the directing layer for redesign;
4. task coverage and CUT geometry remain separate downstream validators;
5. exact focal-length numbers remain soft visual hints rather than hard spatial controls.

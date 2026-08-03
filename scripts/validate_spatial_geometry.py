#!/usr/bin/env python3
"""Validate subject/target/movement/camera geometry before shot design."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Iterable

EPSILON = 1e-9

VISIBLE_FACE_ALIASES = {
    "front": {"front"},
    "near_front": {"near_front"},
    "front_or_near_front": {"front", "near_front"},
    "three_quarter_front": {"near_front"},
    "side": {"side"},
    "near_back": {"near_back"},
    "three_quarter_back": {"near_back"},
    "back": {"back"},
    "正面": {"front"},
    "近正面": {"near_front"},
    "正面或近正面": {"front", "near_front"},
    "前三分之二": {"near_front"},
    "侧面": {"side"},
    "后三分之二": {"near_back"},
    "背面": {"back"},
}

MOVEMENT_MODES = {
    "forward",
    "backward",
    "lateral",
    "stationary",
    "前进",
    "后退",
    "侧移",
    "静止",
}

DISTANCE_RELATIONS = {
    "toward",
    "away",
    "unchanged",
    "靠近",
    "远离",
    "不变",
}


def load_payload(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def vector(value: object, field: str, errors: list[str]) -> tuple[float, float, float] | None:
    if not isinstance(value, list) or len(value) not in {2, 3}:
        errors.append(f"{field} 必须是2维或3维数字数组")
        return None
    try:
        numbers = [float(item) for item in value]
    except (TypeError, ValueError):
        errors.append(f"{field} 必须只包含数字")
        return None
    if len(numbers) == 2:
        numbers.append(0.0)
    return numbers[0], numbers[1], numbers[2]


def string_list(value: object, field: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{field} 必须是字符串数组")
        return []
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))


def subtract(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def magnitude(v: tuple[float, float, float]) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def normalize(v: tuple[float, float, float], field: str, errors: list[str]) -> tuple[float, float, float] | None:
    size = magnitude(v)
    if size <= EPSILON:
        errors.append(f"{field} 不能是零向量")
        return None
    return v[0] / size, v[1] / size, v[2] / size


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def relation(score: float) -> str:
    if score >= 0.85:
        return "same"
    if score >= 0.35:
        return "oblique_same"
    if score > -0.35:
        return "perpendicular"
    if score > -0.85:
        return "oblique_opposite"
    return "opposite"


def visible_face(score: float) -> str:
    mapping = {
        "same": "front",
        "oblique_same": "near_front",
        "perpendicular": "side",
        "oblique_opposite": "near_back",
        "opposite": "back",
    }
    return mapping[relation(score)]


def movement_relation(score: float) -> str:
    if score >= 0.65:
        return "forward"
    if score <= -0.65:
        return "backward"
    if abs(score) <= 0.35:
        return "lateral"
    return "oblique"


def distance_relation(score: float, movement_size: float) -> str:
    if movement_size <= EPSILON:
        return "unchanged"
    if score >= 0.15:
        return "toward"
    if score <= -0.15:
        return "away"
    return "unchanged"


def canonical_movement_mode(value: str) -> str:
    return {
        "前进": "forward",
        "后退": "backward",
        "侧移": "lateral",
        "静止": "stationary",
    }.get(value, value)


def canonical_distance_relation(value: str) -> str:
    return {
        "靠近": "toward",
        "远离": "away",
        "不变": "unchanged",
    }.get(value, value)


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    scene_id = str(payload.get("scene_id", "")).strip()
    time_id = str(payload.get("time_id", "")).strip()
    if not scene_id:
        errors.append("缺少 scene_id")
    if not time_id:
        errors.append("缺少 time_id")

    scene_anchors = payload.get("scene_anchors")
    if not isinstance(scene_anchors, dict) or not scene_anchors:
        errors.append("scene_anchors 必须是非空对象")
        scene_anchors = {}

    subject = payload.get("subject")
    if not isinstance(subject, dict):
        errors.append("subject 必须是对象")
        subject = {}

    subject_id = str(subject.get("id", "")).strip()
    if not subject_id:
        errors.append("subject.id 不能为空")

    subject_position = vector(subject.get("position"), "subject.position", errors)
    facing_raw = vector(subject.get("facing"), "subject.facing", errors)
    movement_raw = vector(subject.get("movement"), "subject.movement", errors)

    targets = payload.get("targets")
    if not isinstance(targets, dict) or not targets:
        errors.append("targets 必须是非空对象")
        targets = {}

    story_target_id = str(subject.get("story_target", "")).strip()
    gaze_target_id = str(subject.get("gaze_target", story_target_id)).strip()
    distance_target_id = str(subject.get("distance_target", story_target_id)).strip()

    if not story_target_id:
        errors.append("subject.story_target 不能为空")
    if story_target_id not in targets:
        errors.append(f"subject.story_target 引用未知目标：{story_target_id}")
    if gaze_target_id and gaze_target_id not in targets:
        errors.append(f"subject.gaze_target 引用未知目标：{gaze_target_id}")
    if distance_target_id and distance_target_id not in targets:
        errors.append(f"subject.distance_target 引用未知目标：{distance_target_id}")

    target_position = None
    if story_target_id in targets and isinstance(targets[story_target_id], dict):
        target_position = vector(
            targets[story_target_id].get("position"),
            f"targets.{story_target_id}.position",
            errors,
        )

    camera = payload.get("camera")
    if not isinstance(camera, dict):
        errors.append("camera 必须是对象")
        camera = {}
    camera_id = str(camera.get("id", "")).strip()
    if not camera_id:
        errors.append("camera.id 不能为空")
    camera_zone_id = str(camera.get("zone_id", "")).strip()
    if not camera_zone_id:
        errors.append("camera.zone_id 不能为空")
    camera_position = vector(
        camera.get("position_world"), "camera.position_world", errors
    )
    camera_forward = vector(
        camera.get("forward_world"), "camera.forward_world", errors
    )
    primary_scene_anchor_id = str(
        camera.get("primary_scene_anchor_id", "")
    ).strip()
    if not primary_scene_anchor_id:
        errors.append("camera.primary_scene_anchor_id 不能为空")
    elif primary_scene_anchor_id not in scene_anchors:
        errors.append(
            f"camera.primary_scene_anchor_id 引用未知锚点：{primary_scene_anchor_id}"
        )
    visible_anchor_ids = string_list(
        camera.get("visible_anchor_ids"), "camera.visible_anchor_ids", errors
    )
    for anchor_id in visible_anchor_ids:
        if anchor_id not in scene_anchors:
            errors.append(f"camera.visible_anchor_ids 引用未知锚点：{anchor_id}")
    if primary_scene_anchor_id and primary_scene_anchor_id not in visible_anchor_ids:
        errors.append("主要场景锚点必须同时存在于 visible_anchor_ids")

    primary_anchor_position = None
    if primary_scene_anchor_id in scene_anchors and isinstance(
        scene_anchors.get(primary_scene_anchor_id), dict
    ):
        primary_anchor_position = vector(
            scene_anchors[primary_scene_anchor_id].get("position"),
            f"scene_anchors.{primary_scene_anchor_id}.position",
            errors,
        )

    if all(item is not None for item in (camera_position, camera_forward, primary_anchor_position)):
        assert camera_position is not None
        assert camera_forward is not None
        assert primary_anchor_position is not None
        normalized_forward = normalize(camera_forward, "camera.forward_world", errors)
        anchor_direction = normalize(
            subtract(primary_anchor_position, camera_position),
            f"camera→scene_anchors.{primary_scene_anchor_id}",
            errors,
        )
        if normalized_forward is not None and anchor_direction is not None:
            if dot(normalized_forward, anchor_direction) < 0.5:
                errors.append("camera.forward_world 没有朝向主要场景锚点")

    movement_mode_raw = str(subject.get("movement_mode", "")).strip()
    if movement_mode_raw not in MOVEMENT_MODES:
        errors.append("subject.movement_mode 必须是 forward/backward/lateral/stationary 或中文对应值")
    movement_mode = canonical_movement_mode(movement_mode_raw)

    claimed_distance_raw = str(subject.get("distance_relation", "")).strip()
    if claimed_distance_raw not in DISTANCE_RELATIONS:
        errors.append("subject.distance_relation 必须是 toward/away/unchanged 或中文对应值")
    claimed_distance = canonical_distance_relation(claimed_distance_raw)

    claimed_face_raw = str(camera.get("claimed_visible_face", "")).strip()
    allowed_faces = VISIBLE_FACE_ALIASES.get(claimed_face_raw)
    if allowed_faces is None:
        errors.append(
            "camera.claimed_visible_face 必须是 front/near_front/front_or_near_front/side/near_back/back 或中文对应值"
        )
        allowed_faces = set()

    locked_solution = payload.get("locked_solution")
    if not isinstance(locked_solution, bool):
        errors.append("locked_solution 必须是布尔值")
        locked_solution = False
    alternatives = payload.get("alternative_camera_solutions", [])
    if not isinstance(alternatives, list):
        errors.append("alternative_camera_solutions 必须是数组")
        alternatives = []
    if locked_solution and alternatives:
        errors.append("唯一方案锁已开启，不得同时提供替代摄影机方案")

    derived: dict[str, object] = {}

    if all(item is not None for item in (subject_position, facing_raw, movement_raw, target_position, camera_position)):
        assert subject_position is not None
        assert facing_raw is not None
        assert movement_raw is not None
        assert target_position is not None
        assert camera_position is not None

        facing = normalize(facing_raw, "subject.facing", errors)
        target_direction = normalize(
            subtract(target_position, subject_position),
            f"subject→targets.{story_target_id}",
            errors,
        )
        camera_direction = normalize(
            subtract(camera_position, subject_position),
            "subject→camera",
            errors,
        )
        movement_size = magnitude(movement_raw)
        movement = None
        if movement_size > EPSILON:
            movement = normalize(movement_raw, "subject.movement", errors)

        if facing is not None and target_direction is not None and camera_direction is not None:
            facing_target_score = dot(facing, target_direction)
            camera_facing_score = dot(camera_direction, facing)
            camera_target_score = dot(camera_direction, target_direction)

            derived_face = visible_face(camera_facing_score)
            derived["facing_to_story_target"] = relation(facing_target_score)
            derived["camera_to_facing"] = relation(camera_facing_score)
            derived["visible_face"] = derived_face
            derived["camera_to_story_target_direction"] = relation(camera_target_score)

            require_faces_target = subject.get("must_face_story_target", True)
            if require_faces_target is True and facing_target_score < 0.85:
                errors.append(
                    f"{subject_id or '人物'}未正面朝向剧情对象{story_target_id}；"
                    f"方向关系={relation(facing_target_score)}"
                )

            if allowed_faces and derived_face not in allowed_faces:
                errors.append(
                    f"摄影机方位只能看到{derived_face}，却声明为{claimed_face_raw}"
                )

            camera_same_direction_claim = camera.get("same_direction_as_story_target")
            if camera_same_direction_claim is True and camera_target_score < 0.85:
                errors.append("摄影机并不位于剧情对象方向，不能声明同方向反拍")
            if camera_same_direction_claim is False and camera_target_score >= 0.85:
                warnings.append("摄影机实际与剧情对象同方向，但声明为不同方向")

            gaze_to_lens_claim = camera.get("subject_appears_to_look_toward_lens")
            if gaze_to_lens_claim is True:
                if gaze_target_id not in targets or not isinstance(targets.get(gaze_target_id), dict):
                    errors.append("无法验证视线动机：gaze_target 无有效坐标")
                else:
                    gaze_position = vector(
                        targets[gaze_target_id].get("position"),
                        f"targets.{gaze_target_id}.position",
                        errors,
                    )
                    if gaze_position is not None:
                        gaze_direction = normalize(
                            subtract(gaze_position, subject_position),
                            f"subject→targets.{gaze_target_id}",
                            errors,
                        )
                        if gaze_direction is not None:
                            gaze_camera_score = dot(gaze_direction, camera_direction)
                            motivated = gaze_camera_score >= 0.90
                            derived["lens_gaze_motivated"] = motivated
                            if not motivated:
                                errors.append(
                                    "人物看向剧情对象的方向与摄影机方向不一致；"
                                    "当前近似看镜头属于无动机看镜头"
                                )

        if facing is not None:
            if movement_size <= EPSILON:
                derived_movement_mode = "stationary"
                movement_facing_score = 0.0
            else:
                assert movement is not None
                movement_facing_score = dot(movement, facing)
                derived_movement_mode = movement_relation(movement_facing_score)
            derived["movement_to_facing"] = derived_movement_mode

            if movement_mode == "stationary" and movement_size > EPSILON:
                errors.append("声明静止，但 subject.movement 不是零向量")
            elif movement_mode != "stationary" and derived_movement_mode != movement_mode:
                errors.append(
                    f"人物移动实际为{derived_movement_mode}，却声明为{movement_mode}"
                )

        if target_direction is not None:
            if movement_size <= EPSILON:
                derived_distance = "unchanged"
            else:
                assert movement is not None
                derived_distance = distance_relation(dot(movement, target_direction), movement_size)
            derived["distance_relation"] = derived_distance
            if claimed_distance and derived_distance != claimed_distance:
                errors.append(
                    f"人物相对剧情对象实际为{derived_distance}，却声明为{claimed_distance}"
                )

    return {
        "ok": not errors,
        "scene_id": scene_id,
        "time_id": time_id,
        "subject_id": subject_id,
        "camera_id": camera_id,
        "camera_zone_id": camera_zone_id,
        "observation_signature": {
            "camera_position_world": list(camera_position) if camera_position else None,
            "camera_forward_world": list(camera_forward) if camera_forward else None,
            "primary_scene_anchor_id": primary_scene_anchor_id,
            "visible_anchor_ids": sorted(visible_anchor_ids),
        },
        "locked_solution": locked_solution,
        "derived": derived,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="?", help="JSON file; omit to read stdin")
    args = parser.parse_args()
    try:
        payload = load_payload(args.json_file)
        result = validate(payload)
    except (OSError, json.JSONDecodeError) as exc:
        result = {"ok": False, "errors": [f"无法读取JSON：{exc}"], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

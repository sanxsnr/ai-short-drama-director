#!/usr/bin/env python3
"""Validate visual-difference paths between adjacent camera shots."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Iterable

EPSILON = 1e-9

SCALE_LEVELS = {
    "EWS": 0,
    "EXTREME_WIDE": 0,
    "大远景": 0,
    "WS": 1,
    "WIDE": 1,
    "远景": 1,
    "全景": 1,
    "MWS": 2,
    "MEDIUM_WIDE": 2,
    "中远景": 2,
    "MS": 3,
    "MEDIUM": 3,
    "中景": 3,
    "MCU": 4,
    "MEDIUM_CLOSE": 4,
    "中近景": 4,
    "CU": 5,
    "CLOSE": 5,
    "近景": 5,
    "BCU": 6,
    "BIG_CLOSE": 6,
    "特写": 6,
    "ECU": 7,
    "EXTREME_CLOSE": 7,
    "大特写": 7,
    "极近特写": 7,
    "眼部极近特写": 7,
}

CLAIMED_PATHS = {
    "angle",
    "axial_scale",
    "subject_or_viewpoint",
    "combined",
    "intentional_jump",
    "角度",
    "同轴大景别",
    "主体或视角变化",
    "组合差异",
    "有意跳切",
}

VISUAL_CHANGE_ALIASES = {
    "camera_height",
    "composition_center",
    "spatial_layering",
    "focus_target",
    "character_relationship",
    "screen_relation",
    "lens_perspective",
    "background_relation",
    "摄影机高度",
    "构图重心",
    "空间层次",
    "焦点主体",
    "人物关系",
    "屏幕关系",
    "透视关系",
    "背景关系",
}

NARRATIVE_CHANGE_ALIASES = {
    "action_stage",
    "new_information",
    "emotion_or_power_focus",
    "动作阶段",
    "新增信息",
    "情绪或权力重点",
}

PATH_CANONICAL = {
    "角度": "angle",
    "同轴大景别": "axial_scale",
    "主体或视角变化": "subject_or_viewpoint",
    "组合差异": "combined",
    "有意跳切": "intentional_jump",
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
    result = numbers[0], numbers[1], numbers[2]
    if math.sqrt(sum(item * item for item in result)) <= EPSILON:
        errors.append(f"{field} 不能是零向量")
        return None
    return result


def normalize(value: tuple[float, float, float]) -> tuple[float, float, float]:
    size = math.sqrt(sum(item * item for item in value))
    return tuple(item / size for item in value)  # type: ignore[return-value]


def angle_degrees(
    first: tuple[float, float, float], second: tuple[float, float, float]
) -> float:
    a = normalize(first)
    b = normalize(second)
    score = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))
    return math.degrees(math.acos(score))


def scale_level(value: object, field: str, errors: list[str]) -> int | None:
    key = str(value or "").strip()
    if key in SCALE_LEVELS:
        return SCALE_LEVELS[key]
    upper = key.upper()
    if upper in SCALE_LEVELS:
        return SCALE_LEVELS[upper]
    errors.append(f"{field} 使用未知景别：{key!r}")
    return None


def text_list(value: object, field: str, errors: list[str]) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{field} 必须是字符串数组")
        return []
    return [item.strip() for item in value if item.strip()]


def canonical_path(value: str) -> str:
    return PATH_CANONICAL.get(value, value)


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    from_shot = payload.get("from_shot")
    to_shot = payload.get("to_shot")
    if not isinstance(from_shot, dict):
        errors.append("from_shot 必须是对象")
        from_shot = {}
    if not isinstance(to_shot, dict):
        errors.append("to_shot 必须是对象")
        to_shot = {}

    for name, shot in (("from_shot", from_shot), ("to_shot", to_shot)):
        if not str(shot.get("id", "")).strip():
            errors.append(f"{name}.id 不能为空")
        if not str(shot.get("primary_subject", "")).strip():
            errors.append(f"{name}.primary_subject 不能为空")
        if not str(shot.get("time_space", "")).strip():
            errors.append(f"{name}.time_space 不能为空")
        if not str(shot.get("viewpoint", "")).strip():
            errors.append(f"{name}.viewpoint 不能为空")
        if not str(shot.get("action_stage", "")).strip():
            errors.append(f"{name}.action_stage 不能为空")

    from_vector = vector(
        from_shot.get("subject_to_camera"),
        "from_shot.subject_to_camera",
        errors,
    )
    to_vector = vector(
        to_shot.get("subject_to_camera"),
        "to_shot.subject_to_camera",
        errors,
    )
    from_scale = scale_level(from_shot.get("shot_scale"), "from_shot.shot_scale", errors)
    to_scale = scale_level(to_shot.get("shot_scale"), "to_shot.shot_scale", errors)

    independent_task = payload.get("independent_task")
    if not isinstance(independent_task, bool):
        errors.append("independent_task 必须是布尔值")
        independent_task = False
    if independent_task is False:
        errors.append("下一SHOT没有独立叙事任务，CUT不成立")

    intentional_jump = payload.get("intentional_jump_cut", False)
    if not isinstance(intentional_jump, bool):
        errors.append("intentional_jump_cut 必须是布尔值")
        intentional_jump = False

    declared_changes = text_list(
        payload.get("declared_changes"), "declared_changes", errors
    )
    unknown_changes = [
        item
        for item in declared_changes
        if item not in VISUAL_CHANGE_ALIASES and item not in NARRATIVE_CHANGE_ALIASES
    ]
    for item in unknown_changes:
        warnings.append(f"declared_changes 包含未标准化变化项：{item}")

    claimed_path_raw = str(payload.get("claimed_difference_path", "")).strip()
    if claimed_path_raw and claimed_path_raw not in CLAIMED_PATHS:
        errors.append(
            "claimed_difference_path 必须是 angle/axial_scale/subject_or_viewpoint/"
            "combined/intentional_jump 或中文对应值"
        )
    claimed_path = canonical_path(claimed_path_raw)

    angle = None
    scale_steps = None
    if from_vector is not None and to_vector is not None:
        angle = angle_degrees(from_vector, to_vector)
    if from_scale is not None and to_scale is not None:
        scale_steps = abs(from_scale - to_scale)

    same_subject = (
        str(from_shot.get("primary_subject", "")).strip()
        == str(to_shot.get("primary_subject", "")).strip()
    )
    same_time_space = (
        str(from_shot.get("time_space", "")).strip()
        == str(to_shot.get("time_space", "")).strip()
    )
    viewpoint_changed = (
        str(from_shot.get("viewpoint", "")).strip()
        != str(to_shot.get("viewpoint", "")).strip()
    )
    action_stage_changed = (
        str(from_shot.get("action_stage", "")).strip()
        != str(to_shot.get("action_stage", "")).strip()
    )

    derived_path = None
    thirty_degree_applicable = False
    difference_strength = "insufficient"
    moderate_changes: list[str] = []

    if intentional_jump:
        derived_path = "intentional_jump"
        difference_strength = "intentional"
    elif not same_subject or not same_time_space or viewpoint_changed:
        derived_path = "subject_or_viewpoint"
        difference_strength = "strong"
    elif angle is not None and angle >= 30.0:
        derived_path = "angle"
        thirty_degree_applicable = True
        difference_strength = "strong"
    elif scale_steps is not None and scale_steps >= 2:
        derived_path = "axial_scale"
        difference_strength = "strong"
    else:
        # The 30-degree rule matters most when subject/time/viewpoint match and scale is same/adjacent.
        thirty_degree_applicable = same_subject and same_time_space and not viewpoint_changed
        if angle is not None and 15.0 <= angle < 30.0:
            moderate_changes.append("camera_angle_15_29")
        if scale_steps == 1:
            moderate_changes.append("adjacent_scale_change")
        moderate_changes.extend(
            item for item in declared_changes if item in VISUAL_CHANGE_ALIASES
        )
        if action_stage_changed:
            moderate_changes.append("action_stage")
        moderate_changes.extend(
            item for item in declared_changes if item in NARRATIVE_CHANGE_ALIASES
        )
        moderate_changes = list(dict.fromkeys(moderate_changes))

        visual_count = sum(
            1
            for item in moderate_changes
            if item in VISUAL_CHANGE_ALIASES
            or item in {"camera_angle_15_29", "adjacent_scale_change"}
        )
        if len(moderate_changes) >= 2 and visual_count >= 1:
            derived_path = "combined"
            difference_strength = "combined"
        else:
            derived_path = "invalid_near_jump"
            if angle is not None and angle < 15.0 and (scale_steps or 0) <= 1:
                errors.append(
                    "前后SHOT为同一主体与连续时空，摄影机夹角小于15度，"
                    "景别相同或只差一级，且缺少足够组合差异；属于无意近似跳切"
                )
            else:
                errors.append("相邻SHOT缺少一条合法视觉差异路径")

    if claimed_path and claimed_path != derived_path:
        errors.append(
            f"声明的视觉差异路径为{claimed_path}，但几何推导结果为{derived_path}"
        )

    if derived_path == "intentional_jump" and not str(
        payload.get("jump_cut_purpose", "")
    ).strip():
        errors.append("有意跳切必须填写 jump_cut_purpose")

    if derived_path == "axial_scale" and angle is not None and angle > 30.0:
        warnings.append("当前同时满足角度路径与大景别路径；优先记录角度路径即可")

    if derived_path == "angle":
        thirty_degree_status = "met"
    elif derived_path == "combined" and thirty_degree_applicable:
        thirty_degree_status = "not_met_but_combined_path"
    elif derived_path == "invalid_near_jump" and thirty_degree_applicable:
        thirty_degree_status = "not_met"
    elif derived_path == "intentional_jump":
        thirty_degree_status = "not_applicable_intentional_jump"
    else:
        thirty_degree_status = "not_applicable"

    return {
        "ok": not errors,
        "from_shot": from_shot.get("id"),
        "to_shot": to_shot.get("id"),
        "camera_angle_degrees": round(angle, 2) if angle is not None else None,
        "shot_scale_step_difference": scale_steps,
        "same_primary_subject": same_subject,
        "same_time_space": same_time_space,
        "viewpoint_changed": viewpoint_changed,
        "action_stage_changed": action_stage_changed,
        "thirty_degree_applicable": thirty_degree_applicable,
        "thirty_degree_status": thirty_degree_status,
        "derived_difference_path": derived_path,
        "difference_strength": difference_strength,
        "moderate_changes": moderate_changes,
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

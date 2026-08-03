#!/usr/bin/env python3
"""Validate visual-difference paths between adjacent camera shots."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

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
    "MLS": 2,
    "MEDIUM_LONG_SHOT": 2,
    "中全景": 2,
    "MS": 3,
    "MEDIUM": 3,
    "MEDIUM_SHOT": 3,
    "中景": 3,
    "MCU": 4,
    "MEDIUM_CLOSE": 4,
    "MEDIUM_CLOSE_UP": 4,
    "中近景": 4,
    "近景": 4,
    "CU": 5,
    "CLOSE": 5,
    "CLOSE_UP": 5,
    "特写": 5,
    "BCU": 6,
    "BIG_CLOSE": 6,
    "大特写": 6,
    "ECU": 7,
    "EXTREME_CLOSE": 7,
    "EXTREME_CLOSE_UP": 7,
    "极近特写": 7,
    "眼部极近特写": 7,
}

PATH_ALIASES = {
    "angle": "angle",
    "角度": "angle",
    "axial_scale": "axial_scale",
    "同轴大景别": "axial_scale",
    "subject_or_viewpoint": "subject_or_viewpoint",
    "主体或视角变化": "subject_or_viewpoint",
    "combined": "combined",
    "组合差异": "combined",
    "intentional_jump": "intentional_jump",
    "有意跳切": "intentional_jump",
    "graphic_match": "graphic_match",
    "图形匹配": "graphic_match",
}

AXIS_STATUSES = {
    "same_side",
    "reestablished",
    "not_applicable",
    "crossed_without_reestablish",
    "同侧",
    "已重新建立",
    "不适用",
    "越轴未重建",
}

EDITING_DEVICES = {
    "none",
    "intentional_jump_cut",
    "graphic_match",
    "无",
    "有意跳切",
    "图形匹配",
}

OPTIONAL_VISUAL_FIELDS = {
    "camera_height": "camera_height",
    "composition_center": "composition_center",
    "focus_target": "focus_target",
    "spatial_layering": "spatial_layering",
    "relationship_frame": "relationship_frame",
    "screen_relation": "screen_relation",
    "background_relation": "background_relation",
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
    return value[0] / size, value[1] / size, value[2] / size


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


def canonical_path(value: object) -> str:
    return PATH_ALIASES.get(str(value or "").strip(), "")


def canonical_axis(value: object) -> str:
    return {
        "同侧": "same_side",
        "已重新建立": "reestablished",
        "不适用": "not_applicable",
        "越轴未重建": "crossed_without_reestablish",
    }.get(str(value or "").strip(), str(value or "").strip())


def canonical_device(value: object) -> str:
    return {
        "无": "none",
        "有意跳切": "intentional_jump_cut",
        "图形匹配": "graphic_match",
    }.get(str(value or "").strip(), str(value or "").strip())


def time_value(shot: dict) -> str:
    explicit = str(shot.get("time", "")).strip()
    if explicit:
        return explicit
    return str(shot.get("time_space", "")).strip()


def space_value(shot: dict) -> str:
    explicit = str(shot.get("space", "")).strip()
    if explicit:
        return explicit
    return str(shot.get("time_space", "")).strip()


def changed_optional_visual_fields(from_shot: dict, to_shot: dict) -> list[str]:
    changed: list[str] = []
    for field, label in OPTIONAL_VISUAL_FIELDS.items():
        before = from_shot.get(field)
        after = to_shot.get(field)
        if before is None or after is None:
            continue
        if field == "camera_height":
            try:
                if abs(float(before) - float(after)) >= 0.25:
                    changed.append(label)
            except (TypeError, ValueError):
                continue
        elif str(before).strip() != str(after).strip():
            changed.append(label)
    return changed


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    transition_id = str(payload.get("transition_id", "")).strip()
    if not transition_id:
        transition_id = "unnamed-transition"
        warnings.append("缺少 transition_id，已使用临时标识")

    from_shot = payload.get("from_shot")
    to_shot = payload.get("to_shot")
    if not isinstance(from_shot, dict):
        errors.append("from_shot 必须是对象")
        from_shot = {}
    if not isinstance(to_shot, dict):
        errors.append("to_shot 必须是对象")
        to_shot = {}

    for name, shot in (("from_shot", from_shot), ("to_shot", to_shot)):
        for field in ("id", "primary_subject", "viewpoint", "action_stage"):
            if not str(shot.get(field, "")).strip():
                errors.append(f"{name}.{field} 不能为空")
        if not time_value(shot):
            errors.append(f"{name}.time 或 time_space 不能为空")
        if not space_value(shot):
            errors.append(f"{name}.space 或 time_space 不能为空")
        if "camera_height" in shot:
            try:
                float(shot["camera_height"])
            except (TypeError, ValueError):
                errors.append(f"{name}.camera_height 必须是数字")

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
    if not independent_task:
        errors.append("下一SHOT没有独立叙事任务，CUT不成立")

    axis_status_raw = str(payload.get("axis_status", "")).strip()
    if axis_status_raw not in AXIS_STATUSES:
        errors.append(
            "axis_status 必须是 same_side/reestablished/not_applicable/"
            "crossed_without_reestablish 或中文对应值"
        )
    axis_status = canonical_axis(axis_status_raw)
    if axis_status == "crossed_without_reestablish":
        errors.append("180度轴线被无理由跨越；任何30度或景别变化都不能覆盖越轴错误")

    editing_device_raw = str(payload.get("editing_device", "none")).strip()
    if editing_device_raw not in EDITING_DEVICES:
        errors.append(
            "editing_device 必须是 none/intentional_jump_cut/graphic_match 或中文对应值"
        )
    editing_device = canonical_device(editing_device_raw)

    claimed_path_raw = str(payload.get("claimed_difference_path", "")).strip()
    claimed_path = canonical_path(claimed_path_raw)
    if claimed_path_raw and not claimed_path:
        errors.append(
            "claimed_difference_path 必须是 angle/axial_scale/subject_or_viewpoint/"
            "combined/intentional_jump/graphic_match 或中文对应值"
        )

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
    same_time = time_value(from_shot) == time_value(to_shot)
    same_space = space_value(from_shot) == space_value(to_shot)
    viewpoint_changed = (
        str(from_shot.get("viewpoint", "")).strip()
        != str(to_shot.get("viewpoint", "")).strip()
    )
    action_stage_changed = (
        str(from_shot.get("action_stage", "")).strip()
        != str(to_shot.get("action_stage", "")).strip()
    )

    optional_visual_changes = changed_optional_visual_fields(from_shot, to_shot)
    moderate_visual_changes: list[str] = []
    strong_visual_changes: list[str] = []

    if not same_subject:
        strong_visual_changes.append("primary_subject")
    if not same_time:
        strong_visual_changes.append("time")
    if not same_space:
        strong_visual_changes.append("space")
    if viewpoint_changed:
        strong_visual_changes.append("viewpoint")
    if angle is not None:
        if angle >= 30.0:
            strong_visual_changes.append("camera_angle_30_plus")
        elif 15.0 <= angle < 30.0:
            moderate_visual_changes.append("camera_angle_15_29")
    if scale_steps is not None:
        if scale_steps >= 2:
            strong_visual_changes.append("shot_scale_2_plus")
        elif scale_steps == 1:
            moderate_visual_changes.append("shot_scale_1")
    moderate_visual_changes.extend(optional_visual_changes)
    moderate_visual_changes = list(dict.fromkeys(moderate_visual_changes))

    derived_path = "invalid_near_jump"
    difference_strength = "insufficient"

    if editing_device == "intentional_jump_cut":
        derived_path = "intentional_jump"
        difference_strength = "intentional"
        if not str(payload.get("editing_device_purpose", "")).strip():
            errors.append("有意跳切必须填写 editing_device_purpose")
    elif editing_device == "graphic_match":
        derived_path = "graphic_match"
        difference_strength = "intentional"
        if not str(payload.get("editing_device_purpose", "")).strip():
            errors.append("图形匹配必须填写 editing_device_purpose")
        if not str(payload.get("graphic_match_basis", "")).strip():
            errors.append("图形匹配必须填写 graphic_match_basis")
    elif not same_subject or not same_time or not same_space or viewpoint_changed:
        derived_path = "subject_or_viewpoint"
        difference_strength = "strong"
    elif angle is not None and angle >= 30.0:
        derived_path = "angle"
        difference_strength = "strong"
    elif scale_steps is not None and scale_steps >= 2:
        derived_path = "axial_scale"
        difference_strength = "strong"
    elif len(moderate_visual_changes) >= 2:
        derived_path = "combined"
        difference_strength = "combined"
    else:
        errors.append(
            "相邻SHOT缺少合法视觉差异：需要一项强视觉变化，或至少两项中等视觉变化；"
            "动作阶段、新信息和情绪重点只能证明CUT任务，不能代替画面差异"
        )
        if angle is not None and angle < 15.0 and (scale_steps or 0) <= 1:
            errors.append(
                "前后SHOT为同一主体与连续时空，摄影机夹角小于15度，"
                "景别相同或只差一级，且缺少其他中等视觉变化；属于无意近似跳切"
            )

    thirty_degree_applicable = bool(
        same_subject
        and same_time
        and same_space
        and not viewpoint_changed
        and (scale_steps is not None and scale_steps <= 1)
        and editing_device == "none"
    )
    if derived_path == "angle":
        thirty_degree_status = "met"
    elif thirty_degree_applicable and derived_path == "combined":
        thirty_degree_status = "not_met_but_equivalent_visual_path"
    elif thirty_degree_applicable:
        thirty_degree_status = "not_met"
    elif editing_device != "none":
        thirty_degree_status = "not_applicable_editing_device"
    else:
        thirty_degree_status = "not_applicable"

    if claimed_path and claimed_path != derived_path:
        errors.append(
            f"声明的视觉差异路径为{claimed_path}，但几何推导结果为{derived_path}"
        )

    if axis_status == "not_applicable" and bool(payload.get("axis_required", False)):
        errors.append("axis_required=true 时，axis_status 不能为 not_applicable")

    if action_stage_changed and derived_path == "invalid_near_jump":
        warnings.append("动作阶段已经变化，但视觉差异仍不足；叙事变化不能自动豁免近似机位")

    return {
        "ok": not errors,
        "transition_id": transition_id,
        "from_shot": from_shot.get("id"),
        "to_shot": to_shot.get("id"),
        "camera_angle_degrees": round(angle, 2) if angle is not None else None,
        "shot_scale_step_difference": scale_steps,
        "same_primary_subject": same_subject,
        "same_time": same_time,
        "same_space": same_space,
        "viewpoint_changed": viewpoint_changed,
        "action_stage_changed": action_stage_changed,
        "axis_status": axis_status,
        "thirty_degree_applicable": thirty_degree_applicable,
        "thirty_degree_status": thirty_degree_status,
        "derived_difference_path": derived_path,
        "difference_strength": difference_strength,
        "strong_visual_changes": strong_visual_changes,
        "moderate_visual_changes": moderate_visual_changes,
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

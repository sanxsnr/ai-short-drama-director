#!/usr/bin/env python3
"""Validate visual-difference and 30-degree applicability between adjacent SHOTs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCALE_LEVELS = {
    "ECU": 0,
    "EXTREME_CLOSE_UP": 0,
    "极近特写": 0,
    "眼部极近特写": 0,
    "CU": 1,
    "CLOSE_UP": 1,
    "特写": 1,
    "MCU": 2,
    "MEDIUM_CLOSE_UP": 2,
    "近景": 2,
    "MS": 3,
    "MEDIUM_SHOT": 3,
    "中景": 3,
    "MLS": 4,
    "MEDIUM_LONG_SHOT": 4,
    "中全景": 4,
    "FS": 5,
    "FULL_SHOT": 5,
    "全景": 5,
    "LS": 6,
    "LONG_SHOT": 6,
    "远景": 6,
    "ELS": 7,
    "EXTREME_LONG_SHOT": 7,
    "大远景": 7,
}

VISUAL_DIMENSIONS = {
    "camera_angle",
    "shot_scale",
    "primary_subject",
    "observation_perspective",
    "composition_center",
    "camera_height",
    "spatial_layer",
    "relationship",
}

NARRATIVE_DIMENSIONS = {
    "action_stage",
    "new_information",
    "emotional_power_focus",
}

ALLOWED_DIMENSIONS = VISUAL_DIMENSIONS | NARRATIVE_DIMENSIONS

DOMINANT_CHANGES = {
    "same_axis_scale_jump",
    "new_primary_subject",
    "pov_change",
    "time_change",
    "space_change",
    "relationship_reframe",
    "intentional_jump_cut",
    "graphic_match",
}

AXIS_STATUSES = {
    "same_side",
    "reestablished",
    "not_applicable",
    "crossed_without_reestablish",
}

THIRTY_STATUSES = {"applies", "exempt", "not_applicable"}
PATHS = {"standard", "dominant"}


def load_payload(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def require_bool(payload: dict, field: str, errors: list[str]) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        errors.append(f"{field} 必须是布尔值")
        return False
    return value


def scale_level(value: object, field: str, errors: list[str]) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        errors.append(f"{field} 不能为空")
        return None
    key = raw.upper() if raw.isascii() else raw
    level = SCALE_LEVELS.get(key)
    if level is None:
        errors.append(f"{field} 使用未知景别：{raw}")
    return level


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    transition_id = str(payload.get("transition_id", "")).strip()
    if not transition_id:
        errors.append("缺少 transition_id")

    independent_task = require_bool(payload, "independent_task", errors)
    same_primary_subject = require_bool(payload, "same_primary_subject", errors)
    same_time = require_bool(payload, "same_time", errors)
    same_space = require_bool(payload, "same_space", errors)
    same_action_stage = require_bool(payload, "same_action_stage", errors)
    same_observation_perspective = require_bool(
        payload, "same_observation_perspective", errors
    )
    similar_composition = require_bool(payload, "similar_composition", errors)

    before_level = scale_level(payload.get("shot_scale_before"), "shot_scale_before", errors)
    after_level = scale_level(payload.get("shot_scale_after"), "shot_scale_after", errors)
    scale_difference = (
        abs(before_level - after_level)
        if before_level is not None and after_level is not None
        else None
    )

    try:
        camera_angle = float(payload.get("camera_angle_degrees"))
        if not 0 <= camera_angle <= 180:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("camera_angle_degrees 必须是0—180之间的数字")
        camera_angle = 0.0

    axis_status = str(payload.get("axis_status", "")).strip()
    if axis_status not in AXIS_STATUSES:
        errors.append(
            "axis_status 必须是 same_side/reestablished/not_applicable/"
            "crossed_without_reestablish"
        )
    if axis_status == "crossed_without_reestablish":
        errors.append("180度轴线被无理由跨越；30度变化不能覆盖越轴错误")

    path = str(payload.get("visual_difference_path", "")).strip()
    if path not in PATHS:
        errors.append("visual_difference_path 必须是 standard 或 dominant")

    changed_dimensions_raw = payload.get("changed_dimensions", [])
    if not isinstance(changed_dimensions_raw, list) or not all(
        isinstance(item, str) for item in changed_dimensions_raw
    ):
        errors.append("changed_dimensions 必须是字符串数组")
        changed_dimensions: list[str] = []
    else:
        changed_dimensions = list(
            dict.fromkeys(item.strip() for item in changed_dimensions_raw if item.strip())
        )
        unknown = sorted(set(changed_dimensions) - ALLOWED_DIMENSIONS)
        if unknown:
            errors.append("changed_dimensions 包含未知维度：" + ", ".join(unknown))

    editing_device = str(payload.get("editing_device", "none")).strip()
    if editing_device not in {"none", "intentional_jump_cut", "graphic_match"}:
        errors.append("editing_device 必须是 none/intentional_jump_cut/graphic_match")
        editing_device = "none"

    similar_scale = scale_difference is not None and scale_difference <= 1
    thirty_applies = all(
        (
            same_primary_subject,
            same_time,
            same_space,
            same_action_stage,
            similar_scale,
            same_observation_perspective,
            similar_composition,
            editing_device == "none",
        )
    )

    if thirty_applies:
        derived_status = "applies"
    elif not same_primary_subject or not same_time or not same_space:
        derived_status = "not_applicable"
    else:
        derived_status = "exempt"

    claimed_status = str(payload.get("thirty_degree_status", "")).strip()
    if claimed_status not in THIRTY_STATUSES:
        errors.append("thirty_degree_status 必须是 applies/exempt/not_applicable")
    elif claimed_status != derived_status:
        errors.append(
            f"30度适用性声明错误：根据当前SHOT关系应为{derived_status}，"
            f"却声明为{claimed_status}"
        )

    if not independent_task:
        errors.append("下一SHOT缺少独立叙事任务，CUT不成立")

    if thirty_applies and camera_angle < 30:
        errors.append(
            f"30度规则适用，但机位夹角仅{camera_angle:g}度；"
            "不得用近似机位形成无动机跳切"
        )

    if "shot_scale" in changed_dimensions and scale_difference == 0:
        errors.append("changed_dimensions 声称景别变化，但前后景别相同")
    if "primary_subject" in changed_dimensions and same_primary_subject:
        errors.append("changed_dimensions 声称主要主体变化，但 same_primary_subject=true")
    if "observation_perspective" in changed_dimensions and same_observation_perspective:
        errors.append(
            "changed_dimensions 声称观察视角变化，但 same_observation_perspective=true"
        )
    if "action_stage" in changed_dimensions and same_action_stage:
        errors.append("changed_dimensions 声称动作阶段变化，但 same_action_stage=true")
    if "camera_angle" in changed_dimensions and camera_angle < 10:
        warnings.append("机位夹角不足10度，不宜把camera_angle视为有效视觉变化")

    dominant_change = str(payload.get("dominant_change", "")).strip()

    if path == "standard":
        if dominant_change:
            warnings.append("标准两变量路径不需要 dominant_change")
        if len(changed_dimensions) < 2:
            errors.append("标准两变量路径至少需要两个有效变化维度")
        if not (set(changed_dimensions) & VISUAL_DIMENSIONS):
            errors.append("标准两变量路径至少需要一个视觉几何维度")
        if set(changed_dimensions).issubset(NARRATIVE_DIMENSIONS):
            errors.append("不能只靠动作阶段或新增信息在近似构图之间硬切")
    elif path == "dominant":
        if dominant_change not in DOMINANT_CHANGES:
            errors.append(
                "主导变化路径必须声明有效 dominant_change："
                + ", ".join(sorted(DOMINANT_CHANGES))
            )
        elif dominant_change == "same_axis_scale_jump":
            if scale_difference is None or scale_difference < 2:
                errors.append("同轴大景别变化要求景别至少跨越两级")
            if not same_primary_subject or not same_time or not same_space:
                errors.append("同轴大景别变化应保持同一主体、同一时间和同一空间")
        elif dominant_change == "new_primary_subject" and same_primary_subject:
            errors.append("dominant_change=new_primary_subject 但主要主体并未改变")
        elif dominant_change == "pov_change" and same_observation_perspective:
            errors.append("dominant_change=pov_change 但观察视角并未改变")
        elif dominant_change == "time_change" and same_time:
            errors.append("dominant_change=time_change 但时间未改变")
        elif dominant_change == "space_change" and same_space:
            errors.append("dominant_change=space_change 但空间未改变")
        elif dominant_change == "relationship_reframe":
            needed = {"relationship", "composition_center"}
            if not needed.issubset(set(changed_dimensions)):
                errors.append(
                    "relationship_reframe 必须同时改变relationship和composition_center"
                )
        elif dominant_change in {"intentional_jump_cut", "graphic_match"}:
            if editing_device != dominant_change:
                errors.append(
                    f"dominant_change={dominant_change} 时 editing_device 必须一致"
                )

    if thirty_applies and axis_status == "not_applicable":
        errors.append("同一主体连续空间内30度规则适用时，axis_status不能为not_applicable")

    return {
        "ok": not errors,
        "transition_id": transition_id,
        "scale_difference": scale_difference,
        "derived_thirty_degree_status": derived_status,
        "camera_angle_degrees": camera_angle,
        "visual_difference_path": path,
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

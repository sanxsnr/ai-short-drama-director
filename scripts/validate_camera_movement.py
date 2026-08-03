#!/usr/bin/env python3
"""Validate active locked/movement/CUT camera decisions."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MODES = {"locked", "movement", "cut_to_new_shot"}
CONTENT_TYPES = {"normal", "high_speed_action", "fixed_camera_time_passage"}
GENERIC = {"cinematic", "dynamic", "dramatic", "beautiful", "epic", "cool", "电影感", "动态感", "高级感", "更震撼", "好看", "增强电影感"}
CLOSE = {"ECU", "BCU", "CU", "极近特写", "大特写", "特写", "近景"}
REQUIRED_CONTEXT = (
    "same_subject", "same_time", "same_space", "same_observation_task",
    "continuous_reframe_only", "new_independent_task", "movement_path_feasible",
    "movement_has_narrative_value", "cut_narrative_advantage", "time_passage_after_lock",
)
START_END_FIELDS = (
    "start_camera_zone", "start_direction", "start_height", "start_framing", "start_subject_relation",
    "end_camera_zone", "end_direction", "end_height", "end_framing", "end_subject_relation",
)


def load_payload(path: str | None) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else json.load(sys.stdin)


def text(value: object) -> str:
    return str(value or "").strip()


def as_list(value: object) -> list:
    if isinstance(value, list):
        return value
    return [] if value in (None, "") else [value]


def add(items: list[str], codes: list[str], code: str, message: str) -> None:
    items.append(f"{code}: {message}")
    codes.append(code)


def generic(*values: object) -> bool:
    allowed = {re.sub(r"[\s,，。.!！?？;；:/_-]+", "", item.lower()) for item in GENERIC}
    parts = [re.sub(r"[\s,，。.!！?？;；:/_-]+", "", text(v).lower()) for v in values if text(v)]
    return not parts or all(part in allowed for part in parts)


def derive_recommended_mode(context: dict) -> str:
    if context.get("new_independent_task") is True or context.get("cut_narrative_advantage") is True:
        return "cut_to_new_shot"
    if all(context.get(key) is True for key in ("continuous_reframe_only", "movement_path_feasible", "movement_has_narrative_value")):
        return "movement"
    return "locked"


def validate(payload: dict) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    error_codes: list[str] = []
    warning_codes: list[str] = []

    shot_id = text(payload.get("shot_id"))
    if not shot_id:
        add(errors, error_codes, "missing_shot_id", "shot_id不能为空")
    content_type = text(payload.get("segment_content_type"))
    if content_type not in CONTENT_TYPES:
        add(errors, error_codes, "invalid_segment_content_type", "SEG类型无效")
    try:
        duration = float(payload.get("duration_seconds"))
        if duration <= 0:
            raise ValueError
    except (TypeError, ValueError):
        duration = 0.0
        add(errors, error_codes, "invalid_duration_seconds", "duration_seconds必须大于0")

    decision = payload.get("camera_decision") if isinstance(payload.get("camera_decision"), dict) else {}
    mode = text(decision.get("mode"))
    if mode not in MODES:
        add(errors, error_codes, "invalid_camera_decision_mode", "mode必须为locked、movement或cut_to_new_shot")
    reason = text(decision.get("reason"))
    narrative = text(decision.get("narrative_function"))
    if not reason or not narrative:
        add(errors, error_codes, "missing_camera_movement_purpose", "必须说明reason与narrative_function")
    elif generic(reason, narrative):
        add(errors, error_codes, "unmotivated_camera_movement", "不能只用电影感等空泛理由")

    context = payload.get("decision_context") if isinstance(payload.get("decision_context"), dict) else {}
    for field in REQUIRED_CONTEXT:
        if not isinstance(context.get(field), bool):
            add(errors, error_codes, "incomplete_camera_decision_context", f"decision_context.{field}必须为布尔值")
    recommended_mode = derive_recommended_mode(context)
    motion = payload.get("camera_motion") if isinstance(payload.get("camera_motion"), dict) else {}

    if mode == "locked":
        if motion.get("enabled") is True:
            add(errors, error_codes, "locked_camera_has_movement", "locked模式不能启用运镜")

    elif mode == "movement":
        if motion.get("enabled") is not True:
            add(errors, error_codes, "movement_not_enabled", "movement模式必须enabled=true")
        if context.get("new_independent_task") is True or context.get("same_observation_task") is False:
            add(errors, error_codes, "forced_movement_across_distinct_tasks", "不同观察任务不能强行连续运镜")
        if not text(motion.get("movement_type")):
            add(errors, error_codes, "missing_motion_path", "movement_type不能为空")
        for field in START_END_FIELDS:
            if not text(motion.get(field)):
                code = "missing_start_framing" if field.startswith("start_") else "missing_end_framing"
                add(errors, error_codes, code, f"camera_motion.{field}不能为空")
        path = motion.get("path") if isinstance(motion.get("path"), dict) else {}
        if not text(path.get("path_description")) or not as_list(path.get("spatial_axes")):
            add(errors, error_codes, "missing_motion_path", "必须给出path_description与spatial_axes")
        axes = list(dict.fromkeys(text(x).upper() for x in as_list(path.get("spatial_axes")) if text(x)))
        if len(axes) > 2 and not (content_type == "high_speed_action" and context.get("multi_axis_justified") is True and motion.get("action_readability_preserved") is True):
            add(errors, error_codes, "too_many_camera_motion_axes", "普通SEG最多一个主运动轴加一个辅助轴")
        if path.get("path_clear") is not True or context.get("movement_path_feasible") is not True:
            add(errors, error_codes, "impossible_camera_path", "摄影机路径必须连续且可执行")
        if path.get("axis_side_preserved") is not True and path.get("axis_reestablished") is not True:
            add(errors, error_codes, "camera_path_crosses_axis", "必须保持轴侧或明确重建空间")
        if path.get("intersects_subject") is True:
            add(errors, error_codes, "camera_path_intersects_subject", "路径不能穿过人物")
        if path.get("intersects_obstacle") is True:
            add(errors, error_codes, "camera_path_intersects_obstacle", "路径不能穿过障碍")
        speed = motion.get("speed_profile") if isinstance(motion.get("speed_profile"), dict) else {}
        if any(not text(speed.get(k)) for k in ("start_speed", "middle_speed", "end_speed")):
            add(errors, error_codes, "missing_speed_profile", "必须给出起步、中段和结束速度")
        if not text(motion.get("subject_relation_during_move")) or not as_list(motion.get("information_revealed_during_move")):
            add(errors, error_codes, "missing_camera_movement_purpose", "必须说明运镜中的主体关系和信息揭示")
        if motion.get("required_action_during_move") is True and motion.get("action_visible_during_move") is not True:
            add(errors, error_codes, "movement_loses_required_action", "运镜丢失关键动作")
        try:
            move_time = float(motion.get("movement_duration_seconds"))
            minimum = float(motion.get("minimum_required_seconds"))
            if move_time <= 0 or minimum <= 0 or move_time > duration or move_time < minimum:
                raise ValueError
        except (TypeError, ValueError):
            add(errors, error_codes, "movement_duration_insufficient", "运镜时长不足或超过SEG")
        lock = motion.get("lock_after_move")
        if not isinstance(lock, bool):
            add(warnings, warning_codes, "missing_lock_after_move", "应明确到达后是否锁定")
        if context.get("time_passage_after_lock") is True and lock is not True:
            add(errors, error_codes, "missing_lock_after_move", "时间流逝前必须锁定")
        if lock is True:
            try:
                if float(motion.get("lock_duration_seconds")) <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                add(errors, error_codes, "missing_lock_duration", "锁定时长必须大于0")
        if isinstance(payload.get("subject_motion"), dict) and payload["subject_motion"].get("camera_relative_motion_conflict") is True:
            add(errors, error_codes, "camera_and_subject_motion_conflict", "摄影机与人物运动冲突")
        try:
            orbit = abs(float(path.get("orbit_degrees") or 0))
        except (TypeError, ValueError):
            orbit = 0
        if orbit > 60 and text(motion.get("start_framing")).upper() in CLOSE:
            add(warnings, warning_codes, "close_range_large_orbit_risk", "近景大幅环绕风险较高")

    elif mode == "cut_to_new_shot":
        if motion.get("enabled") is True:
            add(errors, error_codes, "cut_candidate_has_continuous_motion", "CUT候选不能同时声明同一变化为连续运镜")
        if context.get("continuous_reframe_only") is True and context.get("movement_path_feasible") is True and context.get("new_independent_task") is not True and context.get("cut_narrative_advantage") is not True:
            add(errors, error_codes, "unnecessary_cut_for_continuous_reframe", "连续重构存在合法路径，不能无理由切镜")
        if context.get("new_independent_task") is not True and context.get("cut_narrative_advantage") is not True:
            add(errors, error_codes, "missing_cut_narrative_advantage", "CUT必须有独立任务或明确优势")

    if mode in MODES and mode != recommended_mode and not text(decision.get("rejected_alternative")):
        add(warnings, warning_codes, "camera_decision_differs_from_gate", "偏离Gate建议时应说明rejected_alternative")

    return {
        "ok": not errors,
        "shot_id": shot_id,
        "selected_mode": mode,
        "recommended_mode": recommended_mode,
        "errors": errors,
        "error_codes": list(dict.fromkeys(error_codes)),
        "warnings": warnings,
        "warning_codes": list(dict.fromkeys(warning_codes)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="?")
    args = parser.parse_args()
    try:
        result = validate(load_payload(args.json_file))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"ok": False, "errors": [f"invalid_json: {exc}"], "error_codes": ["invalid_json"], "warnings": [], "warning_codes": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

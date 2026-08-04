#!/usr/bin/env python3
"""Validate AI-direct SEG structure without confusing motion, scale or focal cues with CUTs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SEGMENT_CONTENT_TYPES = {
    "normal",
    "high_speed_action",
    "fixed_camera_time_passage",
}

HIGH_SPEED_ACTION_NODES = {
    "blade",
    "strike",
    "body_motion",
    "smoke",
    "occlusion",
    "direction_change",
}

FOCAL_TRANSITION_CUES = {
    "continuous_zoom",
    "zoom_in",
    "zoom_out",
    "camera_push_in",
    "camera_pull_back",
    "push_in",
    "pull_back",
    "dolly_in",
    "dolly_out",
    "连续变焦",
    "摄影机推近",
    "摄影机后退",
    "极速后拉",
}


def load_payload(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def text(value: object) -> str:
    return str(value or "").strip()


def frozen(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def append_issue(
    messages: list[str], codes: list[str], code: str, message: str
) -> None:
    messages.append(f"{code}: {message}")
    codes.append(code)


def validate_count_policy(
    segment_content_type: object,
    shot_count: object,
    cut_count: object,
) -> dict[str, object]:
    """Keep the SEG count policy in one executable source of truth."""

    errors: list[str] = []
    error_codes: list[str] = []
    content_type = text(segment_content_type)

    if content_type not in SEGMENT_CONTENT_TYPES:
        append_issue(
            errors,
            error_codes,
            "invalid_segment_content_type",
            "segment_content_type 必须是 normal、high_speed_action 或 "
            "fixed_camera_time_passage",
        )

    if isinstance(shot_count, bool) or not isinstance(shot_count, int) or shot_count < 1:
        append_issue(
            errors,
            error_codes,
            "invalid_shot_count",
            "shot_count 必须是大于0的整数",
        )
    if isinstance(cut_count, bool) or not isinstance(cut_count, int) or cut_count < 0:
        append_issue(
            errors,
            error_codes,
            "invalid_cut_count",
            "cut_count 必须是大于或等于0的整数",
        )

    if errors:
        return {
            "ok": False,
            "errors": errors,
            "error_codes": list(dict.fromkeys(error_codes)),
        }

    if content_type == "normal" and (shot_count > 2 or cut_count > 1):
        append_issue(
            errors,
            error_codes,
            "too_many_shots_for_normal_segment",
            "普通SEG默认使用一个连续SHOT；确有两个独立画面任务时最多两个SHOT、一次CUT",
        )
    elif content_type == "fixed_camera_time_passage" and (
        shot_count != 1 or cut_count != 0
    ):
        append_issue(
            errors,
            error_codes,
            "fixed_camera_time_passage_requires_single_shot",
            "固定机位时间流逝必须保持一个SHOT且没有内部CUT",
        )

    return {
        "ok": not errors,
        "errors": errors,
        "error_codes": list(dict.fromkeys(error_codes)),
    }


def focal_values(shot: dict) -> list[object]:
    raw = shot.get("focal_lengths_mm", shot.get("focal_length_mm"))
    if isinstance(raw, list):
        values: list[object] = []
        seen: set[str] = set()
        for item in raw:
            key = frozen(item)
            if key not in seen:
                values.append(item)
                seen.add(key)
        return values
    return [raw] if raw not in (None, "") else []


def phase_movements(phases: list[dict], shot_id: str) -> str:
    values: list[str] = []
    for phase in phases:
        phase_shot_id = text(phase.get("shot_id"))
        if phase_shot_id and phase_shot_id != shot_id:
            continue
        values.append(text(phase.get("movement")))
    return " ".join(values)


def focal_transition_is_explained(shot: dict, phases: list[dict]) -> bool:
    explanation = " ".join(
        (
            text(shot.get("focal_transition")),
            frozen(shot.get("camera_motion")),
            phase_movements(phases, text(shot.get("shot_id"))),
        )
    ).lower()
    return any(cue.lower() in explanation for cue in FOCAL_TRANSITION_CUES)


def validate(payload: dict) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    error_codes: list[str] = []
    warning_codes: list[str] = []

    segment_id = text(payload.get("segment_id"))
    segment_content_type = text(payload.get("segment_content_type"))
    if not segment_id:
        append_issue(errors, error_codes, "missing_segment_id", "segment_id 不能为空")

    duration_raw = payload.get("duration_seconds")
    try:
        duration_seconds = float(duration_raw)
        if duration_seconds <= 0:
            raise ValueError
    except (TypeError, ValueError):
        duration_seconds = 0.0
        append_issue(
            errors,
            error_codes,
            "invalid_duration_seconds",
            "duration_seconds 必须是大于0的数字",
        )

    shots = payload.get("shots")
    if not isinstance(shots, list) or not shots:
        append_issue(
            errors,
            error_codes,
            "invalid_shots",
            "shots 必须是非空数组",
        )
        shots = []

    declared_shot_count = payload.get("shot_count")
    declared_cut_count = payload.get("cut_count")
    derived_shot_count = len(shots)
    derived_cut_count = max(0, derived_shot_count - 1)

    if declared_shot_count != derived_shot_count:
        append_issue(
            errors,
            error_codes,
            "shot_count_mismatch",
            f"shot_count={declared_shot_count!r}，但显式SHOT边界推导为{derived_shot_count}",
        )
    if declared_cut_count != derived_cut_count:
        append_issue(
            errors,
            error_codes,
            "cut_count_mismatch",
            f"cut_count={declared_cut_count!r}，但显式SHOT边界推导为{derived_cut_count}",
        )

    count_result = validate_count_policy(
        segment_content_type,
        derived_shot_count,
        derived_cut_count,
    )
    errors.extend(count_result["errors"])
    error_codes.extend(count_result["error_codes"])

    raw_phases = payload.get("camera_motion_phases", [])
    if not isinstance(raw_phases, list):
        append_issue(
            errors,
            error_codes,
            "invalid_camera_motion_phases",
            "camera_motion_phases 必须是数组",
        )
        raw_phases = []
    phases: list[dict] = []
    shot_ids = {
        text(shot.get("shot_id"))
        for shot in shots
        if isinstance(shot, dict) and text(shot.get("shot_id"))
    }
    for index, phase in enumerate(raw_phases, start=1):
        if not isinstance(phase, dict):
            append_issue(
                errors,
                error_codes,
                "invalid_camera_motion_phase",
                f"camera_motion_phases[{index}] 必须是对象",
            )
            continue
        phases.append(phase)
        for field in ("start_state", "movement", "end_state"):
            if not text(phase.get(field)):
                append_issue(
                    errors,
                    error_codes,
                    "incomplete_camera_motion_phase",
                    f"camera_motion_phases[{index}].{field} 不能为空",
                )
        if not isinstance(phase.get("lock_after_move"), bool):
            append_issue(
                errors,
                error_codes,
                "incomplete_camera_motion_phase",
                f"camera_motion_phases[{index}].lock_after_move 必须是布尔值",
            )
        phase_shot_id = text(phase.get("shot_id"))
        if phase_shot_id and phase_shot_id not in shot_ids:
            append_issue(
                errors,
                error_codes,
                "unknown_motion_phase_shot",
                f"camera_motion_phases[{index}] 引用了不存在的SHOT：{phase_shot_id}",
            )

    normalized_shots: list[dict] = []
    seen_ids: set[str] = set()
    for index, shot in enumerate(shots, start=1):
        if not isinstance(shot, dict):
            append_issue(
                errors,
                error_codes,
                "invalid_shot",
                f"shots[{index}] 必须是对象",
            )
            continue
        normalized_shots.append(shot)
        shot_id = text(shot.get("shot_id"))
        if not shot_id:
            append_issue(
                errors,
                error_codes,
                "missing_shot_id",
                f"shots[{index}].shot_id 不能为空",
            )
        elif shot_id in seen_ids:
            append_issue(
                errors,
                error_codes,
                "duplicate_shot_id",
                f"SHOT编号重复：{shot_id}",
            )
        else:
            seen_ids.add(shot_id)

        for field in (
            "shot_task",
            "camera_region",
            "camera_station",
            "camera_direction",
            "shot_size",
            "camera_motion",
            "focal_feel",
            "action_stage",
        ):
            value = shot.get(field)
            if value in (None, "", [], {}):
                append_issue(
                    errors,
                    error_codes,
                    "incomplete_shot_structure",
                    f"SHOT {shot_id or index}缺少 {field}",
                )
        for field in ("cut_in", "cut_out"):
            if field not in shot:
                append_issue(
                    errors,
                    error_codes,
                    "incomplete_shot_structure",
                    f"SHOT {shot_id or index}必须显式提供 {field}，无CUT时使用null",
                )

        if index > 1 and shot.get("cut_in") in (None, "", {}):
            append_issue(
                errors,
                error_codes,
                "missing_explicit_cut_boundary",
                f"SHOT {shot_id or index}前存在SHOT边界，必须显式填写 cut_in",
            )
        if index < len(shots) and shot.get("cut_out") in (None, "", {}):
            append_issue(
                errors,
                error_codes,
                "missing_explicit_cut_boundary",
                f"SHOT {shot_id or index}后存在SHOT边界，必须显式填写 cut_out",
            )

        values = focal_values(shot)
        if len(values) > 1 and not focal_transition_is_explained(shot, phases):
            append_issue(
                warnings,
                warning_codes,
                "ambiguous_focal_transition",
                f"SHOT {shot_id or index}列出多个焦段，但没有说明连续变焦、摄影机推近或后退",
            )

    if segment_content_type == "high_speed_action" and normalized_shots:
        stages: set[str] = set()
        signatures: set[str] = set()
        for index, shot in enumerate(normalized_shots, start=1):
            shot_id = text(shot.get("shot_id")) or str(index)
            stage = text(shot.get("action_stage"))
            signature = text(shot.get("action_signature"))
            if stage in stages:
                append_issue(
                    errors,
                    error_codes,
                    "repeated_action_stage",
                    f"高速动作SHOT重复动作阶段：{stage}",
                )
            stages.add(stage)
            if not signature:
                append_issue(
                    errors,
                    error_codes,
                    "missing_action_signature",
                    f"高速动作SHOT {shot_id}必须提供 action_signature",
                )
            elif signature in signatures:
                append_issue(
                    errors,
                    error_codes,
                    "repeated_action",
                    f"高速动作重复同一攻防动作：{signature}",
                )
            signatures.add(signature)
            for field in ("screen_direction", "axis_side", "composition_signature"):
                if not text(shot.get(field)):
                    append_issue(
                        errors,
                        error_codes,
                        "incomplete_high_speed_action_shot",
                        f"高速动作SHOT {shot_id}缺少 {field}",
                    )

            if index == len(normalized_shots):
                continue
            next_shot = normalized_shots[index]
            cut = shot.get("cut_out")
            if not isinstance(cut, dict):
                append_issue(
                    errors,
                    error_codes,
                    "missing_high_speed_cut_evidence",
                    f"高速动作SHOT {shot_id}的 cut_out 必须是证据对象",
                )
                continue
            node_type = text(cut.get("action_node_type"))
            if node_type not in HIGH_SPEED_ACTION_NODES or not text(cut.get("action_node")):
                append_issue(
                    errors,
                    error_codes,
                    "missing_action_cut_node",
                    f"高速动作SHOT {shot_id}的CUT必须落在刀锋、拳脚、身体运动、烟雾、遮挡或方向变化节点",
                )
            for field, code in (
                ("action_progress_continuous", "discontinuous_action_progress"),
                ("screen_direction_continuous", "discontinuous_screen_direction"),
                ("placement_visible", "invisible_reposition"),
                ("visual_difference_sufficient", "near_duplicate_action_cut"),
            ):
                if cut.get(field) is not True:
                    append_issue(
                        errors,
                        error_codes,
                        code,
                        f"高速动作SHOT {shot_id}的CUT必须证明 {field}=true",
                    )
            axis_status = text(cut.get("axis_status"))
            if axis_status not in {"same_side", "reestablished", "not_applicable"}:
                append_issue(
                    errors,
                    error_codes,
                    "cross_axis_in_high_speed_action",
                    f"高速动作SHOT {shot_id}的CUT越轴或未提供合法axis_status",
                )

            before_direction = text(shot.get("screen_direction"))
            after_direction = text(next_shot.get("screen_direction"))
            direction_change_is_visible = bool(
                node_type == "direction_change"
                and cut.get("direction_change_visible") is True
            )
            if before_direction != after_direction and not direction_change_is_visible:
                append_issue(
                    errors,
                    error_codes,
                    "discontinuous_screen_direction",
                    f"高速动作SHOT {shot_id}到下一SHOT的屏幕方向无可见转向过程",
                )

            if (
                text(shot.get("axis_side")) != text(next_shot.get("axis_side"))
                and axis_status != "reestablished"
            ):
                append_issue(
                    errors,
                    error_codes,
                    "cross_axis_in_high_speed_action",
                    f"高速动作SHOT {shot_id}到下一SHOT改变轴线侧但未重新建立空间",
                )

            same_visual_signature = all(
                frozen(shot.get(field)) == frozen(next_shot.get(field))
                for field in ("shot_size", "camera_direction", "composition_signature")
            )
            if same_visual_signature:
                append_issue(
                    errors,
                    error_codes,
                    "near_duplicate_action_cut",
                    f"高速动作SHOT {shot_id}与下一SHOT景别、角度和构图近似",
                )

    time_passage_checks: dict[str, bool] = {}
    if segment_content_type == "fixed_camera_time_passage":
        time_passage = payload.get("time_passage")
        if not isinstance(time_passage, dict):
            append_issue(
                errors,
                error_codes,
                "missing_time_passage_contract",
                "fixed_camera_time_passage 必须提供 time_passage 对象",
            )
            time_passage = {}
        camera_locked = time_passage.get(
            "camera_locked_after_move", time_passage.get("camera_locked")
        )
        geometry_unchanged = time_passage.get(
            "scene_geometry_unchanged", time_passage.get("geometry_unchanged")
        )
        time_passage_checks = {
            "camera_locked_after_move": camera_locked is True,
            "scene_geometry_unchanged": geometry_unchanged is True,
            "character_screen_positions_stable": (
                time_passage.get("character_screen_positions_stable") is True
            ),
            "time_transition_visible": time_passage.get("time_transition_visible") is True,
        }
        if time_passage.get("enabled") is not True:
            append_issue(
                errors,
                error_codes,
                "time_passage_not_enabled",
                "time_passage.enabled 必须为true",
            )
        if not text(time_passage.get("method")):
            append_issue(
                errors,
                error_codes,
                "missing_time_passage_method",
                "time_passage.method 不能为空",
            )
        for field, passed in time_passage_checks.items():
            if not passed:
                append_issue(
                    errors,
                    error_codes,
                    "invalid_fixed_camera_time_passage",
                    f"固定机位时间流逝必须证明 {field}=true",
                )
        if phases and phases[-1].get("lock_after_move") is not True:
            append_issue(
                errors,
                error_codes,
                "camera_not_locked_after_move",
                "摄影机前段移动后，最后一个运镜阶段必须 lock_after_move=true",
            )

    return {
        "ok": not errors,
        "segment_id": segment_id,
        "duration_seconds": duration_seconds,
        "segment_content_type": segment_content_type,
        "shot_count": derived_shot_count,
        "cut_count": derived_cut_count,
        "count_source": "explicit_shot_boundaries_only",
        "camera_motion_phase_count": len(phases),
        "time_passage_checks": time_passage_checks,
        "errors": errors,
        "error_codes": list(dict.fromkeys(error_codes)),
        "warnings": warnings,
        "warning_codes": list(dict.fromkeys(warning_codes)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="?", help="JSON file; omit to read stdin")
    args = parser.parse_args()
    try:
        result = validate(load_payload(args.json_file))
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "ok": False,
            "errors": [f"invalid_json: 无法读取JSON：{exc}"],
            "error_codes": ["invalid_json"],
            "warnings": [],
            "warning_codes": [],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

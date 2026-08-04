#!/usr/bin/env python3
"""Validate CUT geometry only after the next SHOT passes task coverage."""

from __future__ import annotations

import argparse
import importlib.util
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
    "station_or_observation": "station_or_observation",
    "摄影点或观察关系变化": "station_or_observation",
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
    "foreground_subject_id": "foreground_subject_id",
    "background_anchor_id": "background_anchor_id",
    "psychological_distance": "psychological_distance",
}


def load_task_validator():
    path = Path(__file__).with_name("validate_shot_task.py")
    spec = importlib.util.spec_from_file_location("validate_shot_task", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载任务验证器：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TASK_VALIDATOR = load_task_validator()


def load_payload(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def text(value: object) -> str:
    return str(value or "").strip()


def string_list(value: object, field: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{field} 必须是字符串数组")
        return []
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))


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
    key = text(value)
    if key in SCALE_LEVELS:
        return SCALE_LEVELS[key]
    upper = key.upper()
    if upper in SCALE_LEVELS:
        return SCALE_LEVELS[upper]
    errors.append(f"{field} 使用未知景别：{key!r}")
    return None


def canonical_path(value: object) -> str:
    return PATH_ALIASES.get(text(value), "")


def canonical_axis(value: object) -> str:
    return {
        "同侧": "same_side",
        "已重新建立": "reestablished",
        "不适用": "not_applicable",
        "越轴未重建": "crossed_without_reestablish",
    }.get(text(value), text(value))


def canonical_device(value: object) -> str:
    return {
        "无": "none",
        "有意跳切": "intentional_jump_cut",
        "图形匹配": "graphic_match",
    }.get(text(value), text(value))


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
        elif text(before) != text(after):
            changed.append(label)
    return changed


MISSING = object()


def get_path(data: object, dotted_path: str):
    current = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def anchor_overlap(first: list[str], second: list[str]) -> float:
    a, b = set(first), set(second)
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    transition_id = text(payload.get("transition_id")) or "unnamed-transition"
    if transition_id == "unnamed-transition":
        warnings.append("缺少 transition_id，已使用临时标识")

    from_shot = payload.get("from_shot")
    to_shot = payload.get("to_shot")
    if not isinstance(from_shot, dict):
        errors.append("from_shot 必须是对象")
        from_shot = {}
    if not isinstance(to_shot, dict):
        errors.append("to_shot 必须是对象")
        to_shot = {}

    required_fields = (
        "id",
        "primary_subject",
        "viewpoint",
        "action_stage",
        "scene_id",
        "time_id",
        "camera_region_id",
        "primary_scene_anchor_id",
        "camera_station_id",
    )
    for name, shot in (("from_shot", from_shot), ("to_shot", to_shot)):
        for field in required_fields:
            if not text(shot.get(field)):
                errors.append(f"{name}.{field} 不能为空")

    from_camera_position = vector(
        from_shot.get("camera_position_world"),
        "from_shot.camera_position_world",
        errors,
    )
    to_camera_position = vector(
        to_shot.get("camera_position_world"),
        "to_shot.camera_position_world",
        errors,
    )
    from_camera_forward = vector(
        from_shot.get("camera_forward_world"),
        "from_shot.camera_forward_world",
        errors,
    )
    to_camera_forward = vector(
        to_shot.get("camera_forward_world"),
        "to_shot.camera_forward_world",
        errors,
    )
    from_scale = scale_level(from_shot.get("shot_scale"), "from_shot.shot_scale", errors)
    to_scale = scale_level(to_shot.get("shot_scale"), "to_shot.shot_scale", errors)
    from_visible_anchors = string_list(
        from_shot.get("visible_anchor_ids"), "from_shot.visible_anchor_ids", errors
    )
    to_visible_anchors = string_list(
        to_shot.get("visible_anchor_ids"), "to_shot.visible_anchor_ids", errors
    )

    task_contract = to_shot.get("task_contract")
    if not isinstance(task_contract, dict):
        errors.append("to_shot.task_contract 必须是对象，并由14任务覆盖规则验证")
        task_result = {
            "ok": False,
            "derived_independent_task": False,
            "viewpoint_evidence_passed": False,
            "task_type": "",
            "errors": ["缺少task_contract"],
        }
    else:
        task_result = TASK_VALIDATOR.validate(task_contract)
        if not task_result.get("ok"):
            errors.append("下一SHOT未通过14任务覆盖Gate")
            errors.extend(f"任务覆盖：{item}" for item in task_result.get("errors", []))

    task_observation = task_result.get("observation_signature", {})
    task_contract_matches_shot = True
    if task_result.get("scene_id") and text(to_shot.get("scene_id")) != text(task_result.get("scene_id")):
        errors.append("to_shot.scene_id 与 task_contract.scene_id 不一致")
        task_contract_matches_shot = False
    if task_result.get("time_id") and text(to_shot.get("time_id")) != text(task_result.get("time_id")):
        errors.append("to_shot.time_id 与 task_contract.time_id 不一致")
        task_contract_matches_shot = False
    if task_result.get("primary_subject_id") and text(to_shot.get("primary_subject")) != text(task_result.get("primary_subject_id")):
        errors.append("to_shot.primary_subject 与 task_contract.primary_subject_id 不一致")
        task_contract_matches_shot = False
    if isinstance(task_observation, dict):
        if text(to_shot.get("camera_region_id")) != text(task_observation.get("camera_region_id")):
            errors.append("to_shot.camera_region_id 与 task_contract.camera.region_id 不一致")
            task_contract_matches_shot = False
        if text(to_shot.get("camera_station_id")) != text(task_observation.get("camera_station_id")):
            errors.append("to_shot.camera_station_id 与 task_contract.camera.station_id 不一致")
            task_contract_matches_shot = False
        if text(to_shot.get("shot_scale")) != text(task_observation.get("shot_scale")):
            errors.append("to_shot.shot_scale 与 task_contract.camera.shot_scale 不一致")
            task_contract_matches_shot = False
        if text(to_shot.get("foreground_subject_id")) != text(task_observation.get("foreground_subject_id")):
            errors.append("to_shot.foreground_subject_id 与 task_contract不一致")
            task_contract_matches_shot = False
        if text(to_shot.get("background_anchor_id")) != text(task_observation.get("background_anchor_id")):
            errors.append("to_shot.background_anchor_id 与 task_contract不一致")
            task_contract_matches_shot = False
        if text(to_shot.get("psychological_distance")) != text(task_observation.get("psychological_distance")):
            errors.append("to_shot.psychological_distance 与 task_contract不一致")
            task_contract_matches_shot = False
        if text(to_shot.get("primary_scene_anchor_id")) != text(task_observation.get("primary_scene_anchor_id")):
            errors.append("to_shot.primary_scene_anchor_id 与 task_contract不一致")
            task_contract_matches_shot = False
        task_anchor_ids = set(task_observation.get("visible_anchor_ids") or [])
        if task_anchor_ids != set(to_visible_anchors):
            errors.append("to_shot.visible_anchor_ids 与 task_contract不一致")
            task_contract_matches_shot = False
        task_position_raw = task_observation.get("camera_position_world")
        task_forward_raw = task_observation.get("camera_forward_world")
        task_position = vector(task_position_raw, "task_contract.camera.position_world", errors)
        task_forward = vector(task_forward_raw, "task_contract.camera.forward_world", errors)
        if task_position is not None and to_camera_position is not None:
            if magnitude := math.sqrt(sum((a - b) ** 2 for a, b in zip(task_position, to_camera_position))):
                if magnitude > 0.01:
                    errors.append("to_shot.camera_position_world 与 task_contract不一致")
                    task_contract_matches_shot = False
        if task_forward is not None and to_camera_forward is not None:
            if angle_degrees(task_forward, to_camera_forward) > 1.0:
                errors.append("to_shot.camera_forward_world 与 task_contract不一致")
                task_contract_matches_shot = False
    if text(to_shot.get("viewpoint")) != text(task_contract.get("viewpoint") if isinstance(task_contract, dict) else ""):
        errors.append("to_shot.viewpoint 与 task_contract.viewpoint 不一致")
        task_contract_matches_shot = False

    axis_status_raw = text(payload.get("axis_status"))
    if axis_status_raw not in AXIS_STATUSES:
        errors.append(
            "axis_status 必须是 same_side/reestablished/not_applicable/"
            "crossed_without_reestablish 或中文对应值"
        )
    axis_status = canonical_axis(axis_status_raw)
    if axis_status == "crossed_without_reestablish":
        errors.append("180度轴线被无理由跨越；任何视觉变化都不能覆盖越轴错误")

    editing_device_raw = text(payload.get("editing_device")) or "none"
    if editing_device_raw not in EDITING_DEVICES:
        errors.append(
            "editing_device 必须是 none/intentional_jump_cut/graphic_match 或中文对应值"
        )
    editing_device = canonical_device(editing_device_raw)

    claimed_path_raw = text(payload.get("claimed_difference_path"))
    claimed_path = canonical_path(claimed_path_raw)
    if claimed_path_raw and not claimed_path:
        errors.append(
            "claimed_difference_path 必须是 station_or_observation/axial_scale/subject_or_viewpoint/"
            "combined/intentional_jump/graphic_match 或中文对应值"
        )

    observation_direction_change = None
    camera_position_distance = None
    scale_steps = None
    if from_camera_forward is not None and to_camera_forward is not None:
        observation_direction_change = angle_degrees(from_camera_forward, to_camera_forward)
    if from_camera_position is not None and to_camera_position is not None:
        camera_position_distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(from_camera_position, to_camera_position)))
    if from_scale is not None and to_scale is not None:
        scale_steps = abs(from_scale - to_scale)

    same_subject = text(from_shot.get("primary_subject")) == text(
        to_shot.get("primary_subject")
    )
    same_scene = text(from_shot.get("scene_id")) == text(to_shot.get("scene_id"))
    same_time = text(from_shot.get("time_id")) == text(to_shot.get("time_id"))
    viewpoint_changed = text(from_shot.get("viewpoint")) != text(to_shot.get("viewpoint"))
    action_stage_changed = text(from_shot.get("action_stage")) != text(
        to_shot.get("action_stage")
    )
    same_camera_station = text(from_shot.get("camera_station_id")) == text(
        to_shot.get("camera_station_id")
    )
    same_camera_region = text(from_shot.get("camera_region_id")) == text(
        to_shot.get("camera_region_id")
    )
    same_scene_anchor = text(from_shot.get("primary_scene_anchor_id")) == text(
        to_shot.get("primary_scene_anchor_id")
    )
    visible_anchor_overlap = anchor_overlap(from_visible_anchors, to_visible_anchors)
    observation_equivalent = bool(
        same_camera_station
        and same_camera_region
        and same_scene_anchor
        and visible_anchor_overlap >= 0.8
        and (camera_position_distance is None or camera_position_distance <= 0.25)
        and (observation_direction_change is None or observation_direction_change <= 10.0)
    )

    task_passed = bool(task_result.get("derived_independent_task")) and task_contract_matches_shot
    viewpoint_evidence_passed = bool(task_result.get("viewpoint_evidence_passed"))
    viewpoint_fitness_passed = bool(task_result.get("viewpoint_fitness_passed"))
    task_type = text(task_result.get("task_type"))

    if task_type in {"ENTER", "EXIT"} and isinstance(task_contract, dict):
        action = task_contract.get("action", {})
        state_path = text(action.get("state_path")) if isinstance(action, dict) else ""
        start_state = to_shot.get("start_state")
        end_state = to_shot.get("end_state")
        if not isinstance(start_state, dict) or not isinstance(end_state, dict):
            errors.append(f"{task_type}的to_shot必须提供 start_state 与 end_state")
            task_passed = False
        elif state_path:
            before = get_path(start_state, state_path)
            after = get_path(end_state, state_path)
            if before is MISSING or after is MISSING:
                errors.append(f"{task_type}的to_shot状态缺少路径：{state_path}")
                task_passed = False
            else:
                if before != action.get("state_before"):
                    errors.append(
                        f"{task_type}的实际起始状态{before!r}与task_contract.state_before不一致"
                    )
                    task_passed = False
                if after != action.get("state_after"):
                    errors.append(
                        f"{task_type}的实际结束状态{after!r}与task_contract.state_after不一致"
                    )
                    task_passed = False

    if viewpoint_changed and not viewpoint_evidence_passed:
        errors.append("观察视角名称虽然改变，但14未验证真实POV／OTS／INSERT几何证据")

    optional_visual_changes = changed_optional_visual_fields(from_shot, to_shot)
    moderate_visual_changes: list[str] = []
    strong_visual_changes: list[str] = []

    if not same_time:
        strong_visual_changes.append("time_id")
    if not same_scene:
        strong_visual_changes.append("scene_id")
    if viewpoint_changed and viewpoint_evidence_passed:
        strong_visual_changes.append("verified_viewpoint")
    if not same_subject and task_passed:
        strong_visual_changes.append("task_verified_primary_subject")
    if not same_camera_station:
        strong_visual_changes.append("camera_station")
    if scale_steps is not None:
        if scale_steps >= 2:
            strong_visual_changes.append("shot_scale_2_plus")
        elif scale_steps == 1:
            moderate_visual_changes.append("shot_scale_1")
    if not same_camera_region:
        moderate_visual_changes.append("camera_region")
    if not same_scene_anchor:
        moderate_visual_changes.append("scene_anchor")
    moderate_visual_changes.extend(optional_visual_changes)
    moderate_visual_changes = list(dict.fromkeys(moderate_visual_changes))

    derived_path = "invalid_near_jump"
    difference_strength = "insufficient"

    if editing_device == "intentional_jump_cut":
        derived_path = "intentional_jump"
        difference_strength = "intentional"
        if not text(payload.get("editing_device_purpose")):
            errors.append("有意跳切必须填写 editing_device_purpose")
    elif editing_device == "graphic_match":
        derived_path = "graphic_match"
        difference_strength = "intentional"
        if not text(payload.get("editing_device_purpose")):
            errors.append("图形匹配必须填写 editing_device_purpose")
        if not text(payload.get("graphic_match_basis")):
            errors.append("图形匹配必须填写 graphic_match_basis")
    elif not same_scene or not same_time:
        derived_path = "subject_or_viewpoint"
        difference_strength = "strong"
    elif viewpoint_changed and viewpoint_evidence_passed and task_passed:
        derived_path = "subject_or_viewpoint"
        difference_strength = "strong"
    elif not same_subject and task_passed:
        derived_path = "subject_or_viewpoint"
        difference_strength = "strong"
    elif not same_camera_station:
        derived_path = "station_or_observation"
        difference_strength = "strong"
    elif scale_steps is not None and scale_steps >= 2:
        derived_path = "axial_scale"
        difference_strength = "strong"
    elif len(moderate_visual_changes) >= 2:
        derived_path = "combined"
        difference_strength = "combined"
    else:
        errors.append(
            "相邻SHOT缺少合法视觉差异：需要一项强视觉变化，或至少两项中等视觉变化"
        )

    if not task_passed:
        derived_path = "invalid_task_coverage"
        difference_strength = "insufficient"

    if observation_equivalent and not same_subject:
        warnings.append(
            "前后主体虽改变，但场景观察签名近似；CUT只有在14任务覆盖证据真实成立时才允许"
        )

    if claimed_path and claimed_path != derived_path:
        errors.append(
            f"声明的视觉差异路径为{claimed_path}，但推导结果为{derived_path}"
        )

    if axis_status == "not_applicable" and bool(payload.get("axis_required", False)):
        errors.append("axis_required=true 时，axis_status 不能为 not_applicable")

    if action_stage_changed and derived_path in {"invalid_near_jump", "invalid_task_coverage"}:
        warnings.append("动作阶段已经变化，但任务覆盖或视觉差异仍不足")

    return {
        "ok": not errors,
        "transition_id": transition_id,
        "from_shot": from_shot.get("id"),
        "to_shot": to_shot.get("id"),
        "task_type": task_type,
        "task_coverage_passed": task_passed,
        "task_validation": task_result,
        "camera_position_distance": round(camera_position_distance, 3) if camera_position_distance is not None else None,
        "scene_observation_direction_change_degrees": (
            round(observation_direction_change, 2) if observation_direction_change is not None else None
        ),
        "shot_scale_step_difference": scale_steps,
        "same_primary_subject": same_subject,
        "same_scene_id": same_scene,
        "same_time_id": same_time,
        "viewpoint_changed": viewpoint_changed,
        "action_stage_changed": action_stage_changed,
        "observation_equivalent": observation_equivalent,
        "visible_anchor_overlap": round(visible_anchor_overlap, 3),
        "axis_status": axis_status,
        "same_camera_station": same_camera_station,
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
        result = validate(load_payload(args.json_file))
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        result = {"ok": False, "errors": [f"无法验证JSON：{exc}"], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate whether a SHOT completes its task and uses a task-fit viewpoint."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

EPSILON = 1e-9

TASK_TYPES = {
    "ENTER",
    "EXIT",
    "EYELINE_REVEAL",
    "REACTION",
    "CONTACT",
    "PROP_ACTION",
    "MOVEMENT",
    "DIALOGUE",
    "ESTABLISH",
    "OTHER",
}

VIEWPOINT_TYPES = {"objective", "POV", "OTS", "INSERT", "subjective"}


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


def normalize(value: tuple[float, float, float] | None) -> list[float] | None:
    if value is None:
        return None
    size = math.sqrt(sum(item * item for item in value))
    return [round(item / size, 6) for item in value]


def finite_number(value: object, field: str, errors: list[str]) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        errors.append(f"{field} 必须是有限数字")
        return None
    if not math.isfinite(number):
        errors.append(f"{field} 必须是有限数字")
        return None
    return number


def validate_viewpoint(contract: dict, errors: list[str]) -> bool:
    viewpoint = text(contract.get("viewpoint"))
    if viewpoint not in VIEWPOINT_TYPES:
        errors.append("viewpoint 必须是 objective/POV/OTS/INSERT/subjective")
        return False
    if viewpoint == "objective":
        return True

    evidence = contract.get("viewpoint_evidence")
    if not isinstance(evidence, dict):
        errors.append("非客观视角必须提供 viewpoint_evidence 对象")
        return False

    if viewpoint == "POV":
        ok = True
        if not text(evidence.get("source_character_id")):
            errors.append("POV必须提供 source_character_id")
            ok = False
        if evidence.get("camera_origin_matches_character") is not True:
            errors.append("POV必须证明 camera_origin_matches_character=true")
            ok = False
        if evidence.get("target_visible") is not True:
            errors.append("POV必须证明 target_visible=true")
            ok = False
        return ok

    if viewpoint == "OTS":
        ok = True
        if not text(evidence.get("foreground_character_id")):
            errors.append("OTS必须提供 foreground_character_id")
            ok = False
        if evidence.get("foreground_shoulder_visible") is not True:
            errors.append("OTS必须证明 foreground_shoulder_visible=true")
            ok = False
        if not text(evidence.get("focus_subject_id")):
            errors.append("OTS必须提供 focus_subject_id")
            ok = False
        if evidence.get("axis_valid") is not True:
            errors.append("OTS必须证明 axis_valid=true")
            ok = False
        return ok

    if viewpoint == "INSERT":
        ok = True
        if not text(evidence.get("insert_subject_id")):
            errors.append("INSERT必须提供 insert_subject_id")
            ok = False
        if evidence.get("insert_subject_visible") is not True:
            errors.append("INSERT必须证明 insert_subject_visible=true")
            ok = False
        return ok

    if not text(evidence.get("subjective_source_id")):
        errors.append("subjective视角必须提供 subjective_source_id")
        return False
    if evidence.get("subjective_geometry_valid") is not True:
        errors.append("subjective视角必须证明 subjective_geometry_valid=true")
        return False
    return True


def validate_viewpoint_fitness(payload: dict, task_type: str, errors: list[str]) -> bool:
    fitness = payload.get("viewpoint_fitness")
    if not isinstance(fitness, dict):
        errors.append("viewpoint_fitness 必须是对象")
        return False

    required_bools = (
        "task_requires_new_observation",
        "selected_station_serves_task",
        "observation_signature_changed",
        "foreground_relation_changed",
        "psychological_distance_changed",
    )
    values: dict[str, bool] = {}
    for field in required_bools:
        value = fitness.get(field)
        if not isinstance(value, bool):
            errors.append(f"viewpoint_fitness.{field} 必须是布尔值")
            values[field] = False
        else:
            values[field] = value

    if values.get("selected_station_serves_task") is not True:
        errors.append("selected_station_does_not_serve_task")

    changed = any(
        values.get(field) is True
        for field in (
            "observation_signature_changed",
            "foreground_relation_changed",
            "psychological_distance_changed",
        )
    )
    repeat_intent = text(fitness.get("same_station_repetition_intent"))

    if values.get("task_requires_new_observation") is True and not changed and not repeat_intent:
        errors.append("new_observation_not_demonstrated")

    if task_type == "DIALOGUE" and not changed and not repeat_intent:
        errors.append("mechanical_dialogue_view_repetition")

    return not any(
        item in errors
        for item in (
            "selected_station_does_not_serve_task",
            "new_observation_not_demonstrated",
            "mechanical_dialogue_view_repetition",
        )
    )


def validate_enter_exit(
    contract: dict,
    task_type: str,
    camera: dict,
    visible_anchor_ids: list[str],
    errors: list[str],
) -> None:
    action = contract.get("action")
    if not isinstance(action, dict):
        errors.append(f"{task_type}任务必须提供 action 对象")
        return

    actor_id = text(action.get("actor_id"))
    start_zone_id = text(action.get("start_zone_id"))
    boundary_id = text(action.get("boundary_id"))
    end_zone_id = text(action.get("end_zone_id"))
    state_before = text(action.get("state_before"))
    state_after = text(action.get("state_after"))
    state_path = text(action.get("state_path"))

    for field, value in (
        ("action.actor_id", actor_id),
        ("action.start_zone_id", start_zone_id),
        ("action.boundary_id", boundary_id),
        ("action.end_zone_id", end_zone_id),
        ("action.state_before", state_before),
        ("action.state_after", state_after),
        ("action.state_path", state_path),
    ):
        if not value:
            errors.append(f"{field} 不能为空")

    if start_zone_id and end_zone_id and start_zone_id == end_zone_id:
        errors.append(f"{task_type}必须跨越两个不同区域")

    primary_anchor = text(camera.get("primary_scene_anchor_id"))
    if boundary_id and boundary_id not in visible_anchor_ids:
        errors.append(f"{task_type}必须让边界锚点 {boundary_id} 进入画面")
    if boundary_id and primary_anchor != boundary_id:
        errors.append(f"{task_type}的主要场景锚点必须是边界 {boundary_id}，不能只把人物当作锚点")
    if action.get("crossing_visible") is not True:
        errors.append(f"{task_type}必须证明 crossing_visible=true")
    if action.get("path_visible") is not True:
        errors.append(f"{task_type}必须证明 path_visible=true")
    if action.get("movement_crosses_boundary") is not True:
        errors.append(f"{task_type}必须证明 movement_crosses_boundary=true")

    vector(action.get("movement_world"), "action.movement_world", errors)

    if task_type == "ENTER":
        if state_before != "outside":
            errors.append("ENTER的state_before必须是outside，已在室内不得重复进场")
        if state_after != "inside":
            errors.append("完整ENTER任务的state_after必须是inside")
    else:
        if state_before != "inside":
            errors.append("EXIT的state_before必须是inside")
        if state_after != "outside":
            errors.append("完整EXIT任务的state_after必须是outside")


def validate_eyeline_reveal(contract: dict, errors: list[str]) -> None:
    action = contract.get("action")
    if not isinstance(action, dict):
        errors.append("EYELINE_REVEAL必须提供 action 对象")
        return
    if action.get("previous_eyeline_locked") is not True:
        errors.append("EYELINE_REVEAL要求 previous_eyeline_locked=true")
    if not text(action.get("target_id")):
        errors.append("EYELINE_REVEAL必须提供 target_id")
    if action.get("target_visible") is not True:
        errors.append("EYELINE_REVEAL必须证明 target_visible=true")
    if action.get("target_direction_matches") is not True:
        errors.append("EYELINE_REVEAL必须证明 target_direction_matches=true")
    if action.get("target_key_state_visible") is not True:
        errors.append("EYELINE_REVEAL必须展示目标的关键状态或关键动作")


def validate_reaction(contract: dict, errors: list[str]) -> None:
    action = contract.get("action")
    if not isinstance(action, dict):
        errors.append("REACTION必须提供 action 对象")
        return
    if not text(action.get("reaction_cause_id")):
        errors.append("REACTION必须提供 reaction_cause_id")
    if action.get("reaction_visible") is not True:
        errors.append("REACTION必须证明 reaction_visible=true")
    if action.get("reaction_not_completed_before") is not True:
        errors.append("REACTION不得重复上一SHOT已经完成的反应")


def validate_contact(contract: dict, errors: list[str]) -> None:
    action = contract.get("action")
    if not isinstance(action, dict):
        errors.append("CONTACT必须提供 action 对象")
        return
    for field in (
        "actor_id",
        "target_id",
        "contact_point",
        "force_or_transfer_direction",
        "result_state",
    ):
        if not text(action.get(field)):
            errors.append(f"CONTACT必须提供 action.{field}")
    if action.get("contact_visible") is not True:
        errors.append("CONTACT必须证明 contact_visible=true")
    if action.get("result_visible") is not True:
        errors.append("CONTACT必须证明 result_visible=true")


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    shot_id = text(payload.get("shot_id"))
    task_type = text(payload.get("task_type")).upper()
    scene_id = text(payload.get("scene_id"))
    time_id = text(payload.get("time_id"))
    primary_subject_id = text(payload.get("primary_subject_id"))

    for field, value in (
        ("shot_id", shot_id),
        ("task_type", task_type),
        ("scene_id", scene_id),
        ("time_id", time_id),
        ("primary_subject_id", primary_subject_id),
    ):
        if not value:
            errors.append(f"{field} 不能为空")

    if task_type and task_type not in TASK_TYPES:
        errors.append("task_type 使用未知值：" + task_type)

    camera = payload.get("camera")
    if not isinstance(camera, dict):
        errors.append("camera 必须是对象")
        camera = {}

    camera_region_id = text(camera.get("region_id"))
    camera_station_id = text(camera.get("station_id"))
    primary_anchor_id = text(camera.get("primary_scene_anchor_id"))
    if not camera_region_id:
        errors.append("camera.region_id 不能为空")
    if not camera_station_id:
        errors.append("camera.station_id 不能为空")
    if not primary_anchor_id:
        errors.append("camera.primary_scene_anchor_id 不能为空")

    camera_position = vector(camera.get("position_world"), "camera.position_world", errors)
    camera_forward = vector(camera.get("forward_world"), "camera.forward_world", errors)
    camera_height = finite_number(camera.get("height"), "camera.height", errors)

    shot_scale = text(camera.get("shot_scale"))
    foreground_subject_id = text(camera.get("foreground_subject_id"))
    background_anchor_id = text(camera.get("background_anchor_id"))
    motion_mode = text(camera.get("motion_mode"))
    psychological_distance = text(camera.get("psychological_distance"))
    for field, value in (
        ("camera.shot_scale", shot_scale),
        ("camera.background_anchor_id", background_anchor_id),
        ("camera.motion_mode", motion_mode),
        ("camera.psychological_distance", psychological_distance),
    ):
        if not value:
            errors.append(f"{field} 不能为空")

    visible_anchor_ids = string_list(camera.get("visible_anchor_ids"), "camera.visible_anchor_ids", errors)
    if primary_anchor_id and primary_anchor_id not in visible_anchor_ids:
        errors.append("camera.primary_scene_anchor_id 必须同时存在于 visible_anchor_ids")
    if background_anchor_id and background_anchor_id not in visible_anchor_ids:
        errors.append("camera.background_anchor_id 必须同时存在于 visible_anchor_ids")

    required_evidence = string_list(payload.get("required_evidence"), "required_evidence", errors)
    visible_evidence = string_list(payload.get("visible_evidence"), "visible_evidence", errors)
    missing_evidence = sorted(set(required_evidence) - set(visible_evidence))
    if missing_evidence:
        errors.append("SHOT未完成必要任务证据：" + ", ".join(missing_evidence))

    viewpoint_evidence_passed = validate_viewpoint(payload, errors)
    viewpoint_fitness_passed = validate_viewpoint_fitness(payload, task_type, errors)

    if task_type in {"ENTER", "EXIT"}:
        validate_enter_exit(payload, task_type, camera, visible_anchor_ids, errors)
    elif task_type == "EYELINE_REVEAL":
        validate_eyeline_reveal(payload, errors)
    elif task_type == "REACTION":
        validate_reaction(payload, errors)
    elif task_type == "CONTACT":
        validate_contact(payload, errors)
    elif task_type in {"PROP_ACTION", "MOVEMENT"}:
        action = payload.get("action")
        if not isinstance(action, dict):
            errors.append(f"{task_type}必须提供 action 对象")
        else:
            if action.get("action_visible") is not True:
                errors.append(f"{task_type}必须证明 action_visible=true")
            if action.get("result_visible") is not True:
                errors.append(f"{task_type}必须证明 result_visible=true")
            if action.get("repeats_completed_action") is True:
                errors.append(f"{task_type}不得重复上一SHOT已经完成的动作")
    elif task_type == "DIALOGUE":
        action = payload.get("action")
        if not isinstance(action, dict):
            errors.append("DIALOGUE必须提供 action 对象")
        else:
            if not text(action.get("dialogue_focus_reason")):
                errors.append("DIALOGUE必须说明 dialogue_focus_reason，不能只因换说话人而切镜")
            if action.get("focus_subject_visible") is not True:
                errors.append("DIALOGUE必须证明 focus_subject_visible=true")
            if action.get("new_visual_task_visible") is not True:
                errors.append("DIALOGUE必须证明 new_visual_task_visible=true")
            if action.get("mechanical_speaker_switch") is True:
                errors.append("DIALOGUE不得以机械换说话人为独立镜头任务")
    elif task_type == "ESTABLISH":
        action = payload.get("action")
        if not isinstance(action, dict):
            errors.append("ESTABLISH必须提供 action 对象")
        else:
            if action.get("spatial_relationship_visible") is not True:
                errors.append("ESTABLISH必须证明 spatial_relationship_visible=true")
            if action.get("new_anchor_relationship_visible") is not True:
                errors.append("ESTABLISH必须建立新的场景锚点关系")
    elif task_type == "OTHER":
        warnings.append("OTHER任务不会自动支持主体／视角变化路径，应改用明确任务类型")

    derived_independent_task = not errors

    return {
        "ok": not errors,
        "shot_id": shot_id,
        "task_type": task_type,
        "scene_id": scene_id,
        "time_id": time_id,
        "primary_subject_id": primary_subject_id,
        "derived_independent_task": derived_independent_task,
        "viewpoint_evidence_passed": viewpoint_evidence_passed,
        "viewpoint_fitness_passed": viewpoint_fitness_passed,
        "missing_evidence": missing_evidence,
        "observation_signature": {
            "camera_station_id": camera_station_id,
            "camera_region_id": camera_region_id,
            "camera_position_world": list(camera_position) if camera_position else None,
            "camera_forward_world": normalize(camera_forward),
            "camera_height": camera_height,
            "shot_scale": shot_scale,
            "primary_subject_id": primary_subject_id,
            "foreground_subject_id": foreground_subject_id,
            "background_anchor_id": background_anchor_id,
            "viewpoint_type": text(payload.get("viewpoint")),
            "motion_mode": motion_mode,
            "psychological_distance": psychological_distance,
            "primary_scene_anchor_id": primary_anchor_id,
            "visible_anchor_ids": sorted(visible_anchor_ids),
        },
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file", nargs="?", help="JSON file; omit to read stdin")
    args = parser.parse_args()
    try:
        result = validate(load_payload(args.json_file))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"ok": False, "errors": [f"无法读取JSON：{exc}"], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

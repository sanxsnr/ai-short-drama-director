#!/usr/bin/env python3
"""Validate one unified director-authored camera program and its XYZ solve.

The director layer designs SHOT intervals, continuous camera trajectories, and CUT
boundaries together. The spatial layer then solves the plan into camera and actor
keyframes. This validator derives fixed/moving behavior, collision, speed, axis,
and hold results from the coordinates instead of accepting three self-declared
camera modes.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

EPS = 1e-6
SEGMENT_CONTENT_TYPES = {"normal", "high_speed_action", "fixed_camera_time_passage"}
AXIS_POLICIES = {"preserve", "visible_reestablish", "not_applicable"}
CUT_TYPE_INTENTS = {
    "normal", "match_on_action", "reaction", "eyeline", "insert",
    "space", "time", "pov", "occlusion",
}
CUT_MECHANISMS = {"hard_cut", "action_match", "eyeline", "sound_bridge", "occlusion", "dissolve"}
GENERIC_REASONS = {
    "电影感", "更有节奏", "动态感", "高级感", "更震撼", "好看",
    "cinematic", "dynamic", "dramatic", "epic", "beautiful", "cool",
}
DIRECTOR_READ_FIELDS = (
    "scene_function", "dramatic_turn", "pov_empathy",
    "power_movement", "subtext", "scene_intention",
)
TRAJECTORY_FIELDS = (
    "start_composition", "path_intent", "movement_purpose", "speed_rhythm",
    "subject_relation_during_shot", "required_action_visibility",
    "end_composition", "hold_after_arrival_seconds",
)
MOVEMENT_CUES = (
    "推进", "推近", "后退", "拉远", "横移", "跟随", "跟拍", "升高", "降低",
    "摇摄", "环绕", "移动", "轨道", "dolly", "track", "orbit", "crane", "pan",
    "tilt", "truck", "move", "push", "pull",
)
HOLD_CUES = ("固定", "锁定", "保持", "不动", "静止", "hold", "locked", "static")
LEGACY_MODE_VALUES = {"locked", "movement", "cut_to_new_shot"}


def load_coverage_validator():
    path = Path(__file__).with_name("validate_camera_coverage_sequence.py")
    spec = importlib.util.spec_from_file_location("validate_camera_coverage_sequence", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载场景摄影覆盖验证器：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COVERAGE_VALIDATOR = load_coverage_validator()


def load_payload(path: str | None) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8")) if path else json.load(sys.stdin)
    if isinstance(raw, dict) and isinstance(raw.get("directorial_camera_plan"), dict):
        return raw["directorial_camera_plan"]
    return raw


def text(value: object) -> str:
    return str(value or "").strip()


def add(messages: list[str], codes: list[str], code: str, message: str) -> None:
    messages.append(f"{code}: {message}")
    codes.append(code)


def as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def vector(value: object) -> tuple[float, float, float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    values = [as_float(item) for item in value]
    if any(item is None for item in values):
        return None
    return float(values[0]), float(values[1]), float(values[2])


def magnitude(value: tuple[float, float, float]) -> float:
    return math.sqrt(sum(item * item for item in value))


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return magnitude((a[0] - b[0], a[1] - b[1], a[2] - b[2]))


def lerp(a: tuple[float, float, float], b: tuple[float, float, float], ratio: float) -> tuple[float, float, float]:
    return tuple(a[index] + (b[index] - a[index]) * ratio for index in range(3))  # type: ignore[return-value]


def normalized(value: tuple[float, float, float]) -> tuple[float, float, float] | None:
    size = magnitude(value)
    if size <= EPS:
        return None
    return value[0] / size, value[1] / size, value[2] / size


def angle_degrees(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    na, nb = normalized(a), normalized(b)
    if na is None or nb is None:
        return 180.0
    dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(na, nb))))
    return math.degrees(math.acos(dot))


def direction_changed(a: tuple[float, float, float], b: tuple[float, float, float]) -> bool:
    return angle_degrees(a, b) > 1.0


def generic_reason(value: object) -> bool:
    compact = text(value).lower().replace(" ", "")
    allowed = {item.lower().replace(" ", "") for item in GENERIC_REASONS}
    return not compact or compact in allowed


def has_legacy_mode_contract(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"camera_decision", "camera_decision_contract"}:
                return True
            if key == "mode" and text(item) in LEGACY_MODE_VALUES:
                return True
            if has_legacy_mode_contract(item):
                return True
    elif isinstance(value, list):
        return any(has_legacy_mode_contract(item) for item in value)
    return False


def intended_hold(path_intent: str) -> bool:
    lower = path_intent.lower()
    return any(cue.lower() in lower for cue in HOLD_CUES) and not any(
        cue.lower() in lower for cue in MOVEMENT_CUES
    )


def intended_move(path_intent: str) -> bool:
    lower = path_intent.lower()
    return any(cue.lower() in lower for cue in MOVEMENT_CUES)


def in_bounds(position: tuple[float, float, float], bounds: dict[str, tuple[float, float]]) -> bool:
    if len(bounds) != 3:
        return False
    return all(
        bounds[axis][0] - EPS <= position[index] <= bounds[axis][1] + EPS
        for index, axis in enumerate(("x", "y", "z"))
    )


def state_equal(a: dict[str, object], b: dict[str, object]) -> bool:
    pa, pb = vector(a.get("position_world")), vector(b.get("position_world"))
    fa, fb = vector(a.get("forward_world")), vector(b.get("forward_world"))
    if pa is None or pb is None or fa is None or fb is None:
        return False
    return distance(pa, pb) <= EPS and not direction_changed(fa, fb)


def segment_intersects_aabb(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
    clearance: float,
) -> bool:
    expanded_min = tuple(minimum[i] - clearance for i in range(3))
    expanded_max = tuple(maximum[i] + clearance for i in range(3))
    t_min, t_max = 0.0, 1.0
    for axis in range(3):
        delta = end[axis] - start[axis]
        if abs(delta) <= EPS:
            if start[axis] < expanded_min[axis] or start[axis] > expanded_max[axis]:
                return False
            continue
        inv = 1.0 / delta
        t1 = (expanded_min[axis] - start[axis]) * inv
        t2 = (expanded_max[axis] - start[axis]) * inv
        if t1 > t2:
            t1, t2 = t2, t1
        t_min = max(t_min, t1)
        t_max = min(t_max, t2)
        if t_min > t_max:
            return False
    return True


def axis_side(
    position: tuple[float, float, float],
    point_a: tuple[float, float, float],
    point_b: tuple[float, float, float],
) -> float:
    return (
        (point_b[0] - point_a[0]) * (position[1] - point_a[1])
        - (point_b[1] - point_a[1]) * (position[0] - point_a[0])
    )


def interpolate_track(track: list[dict[str, object]], time_value: float) -> tuple[float, float, float] | None:
    if not track:
        return None
    if time_value < float(track[0]["_time"]) - EPS or time_value > float(track[-1]["_time"]) + EPS:
        return None
    for index in range(1, len(track)):
        left, right = track[index - 1], track[index]
        left_t, right_t = float(left["_time"]), float(right["_time"])
        if left_t - EPS <= time_value <= right_t + EPS:
            if right_t - left_t <= EPS:
                return left["_position"]  # type: ignore[return-value]
            ratio = (time_value - left_t) / (right_t - left_t)
            return lerp(left["_position"], right["_position"], ratio)  # type: ignore[arg-type]
    return track[-1]["_position"]  # type: ignore[return-value]


def minimum_synchronous_distance(
    camera_start: tuple[float, float, float],
    camera_end: tuple[float, float, float],
    actor_start: tuple[float, float, float],
    actor_end: tuple[float, float, float],
) -> float:
    """Exact minimum separation for two points moving linearly over the same interval."""
    r0 = tuple(camera_start[i] - actor_start[i] for i in range(3))
    rv = tuple(
        (camera_end[i] - camera_start[i]) - (actor_end[i] - actor_start[i])
        for i in range(3)
    )
    denominator = sum(value * value for value in rv)
    if denominator <= EPS:
        ratio = 0.0
    else:
        ratio = max(0.0, min(1.0, -sum(r0[i] * rv[i] for i in range(3)) / denominator))
    relative = tuple(r0[i] + rv[i] * ratio for i in range(3))
    return magnitude(relative)


def track_overlaps(
    left_start: float,
    left_end: float,
    right_start: float,
    right_end: float,
) -> tuple[float, float] | None:
    start, end = max(left_start, right_start), min(left_end, right_end)
    return (start, end) if end - start > EPS else None


def quadratic_side_samples(
    camera_start: tuple[float, float, float],
    camera_end: tuple[float, float, float],
    axis_a_start: tuple[float, float, float],
    axis_a_end: tuple[float, float, float],
    axis_b_start: tuple[float, float, float],
    axis_b_end: tuple[float, float, float],
) -> list[float]:
    """Evaluate the moving-axis side polynomial at endpoints and its interior extremum."""
    d0 = (axis_b_start[0] - axis_a_start[0], axis_b_start[1] - axis_a_start[1])
    dd = (
        (axis_b_end[0] - axis_a_end[0]) - d0[0],
        (axis_b_end[1] - axis_a_end[1]) - d0[1],
    )
    e0 = (camera_start[0] - axis_a_start[0], camera_start[1] - axis_a_start[1])
    de = (
        (camera_end[0] - axis_a_end[0]) - e0[0],
        (camera_end[1] - axis_a_end[1]) - e0[1],
    )
    c0 = d0[0] * e0[1] - d0[1] * e0[0]
    c1 = d0[0] * de[1] + dd[0] * e0[1] - d0[1] * de[0] - dd[1] * e0[0]
    c2 = dd[0] * de[1] - dd[1] * de[0]
    values = [c0, c0 + c1 + c2]
    if abs(c2) > EPS:
        vertex = -c1 / (2.0 * c2)
        if EPS < vertex < 1.0 - EPS:
            values.append(c0 + c1 * vertex + c2 * vertex * vertex)
    return values


def relationship_axis_side_samples(
    axis_spec: dict[str, object],
    camera_frames: list[dict[str, object]],
    actor_tracks: dict[str, list[dict[str, object]]],
) -> tuple[list[float], str | None]:
    source_type = text(axis_spec.get("source_type"))
    times = {float(frame["_time"]) for frame in camera_frames}
    if source_type == "actor_pair":
        actor_a_id, actor_b_id = text(axis_spec.get("actor_a_id")), text(axis_spec.get("actor_b_id"))
        track_a, track_b = actor_tracks.get(actor_a_id), actor_tracks.get(actor_b_id)
        if not track_a or not track_b:
            return [], f"人物关系轴缺少{actor_a_id}或{actor_b_id}的完整轨迹"
        times.update(float(item["_time"]) for item in track_a)
        times.update(float(item["_time"]) for item in track_b)
    ordered = sorted(times)
    samples: list[float] = []
    for index in range(1, len(ordered)):
        start_time, end_time = ordered[index - 1], ordered[index]
        camera_start = interpolate_track(camera_frames, start_time)
        camera_end = interpolate_track(camera_frames, end_time)
        if camera_start is None or camera_end is None:
            continue
        if source_type == "fixed":
            axis_a_start = axis_a_end = axis_spec.get("point_a")
            axis_b_start = axis_b_end = axis_spec.get("point_b")
        else:
            track_a = actor_tracks[text(axis_spec.get("actor_a_id"))]
            track_b = actor_tracks[text(axis_spec.get("actor_b_id"))]
            axis_a_start, axis_a_end = interpolate_track(track_a, start_time), interpolate_track(track_a, end_time)
            axis_b_start, axis_b_end = interpolate_track(track_b, start_time), interpolate_track(track_b, end_time)
        if not all(isinstance(value, tuple) for value in (axis_a_start, axis_a_end, axis_b_start, axis_b_end)):
            return [], "关系轴在SHOT时间内没有完整关键帧"
        if distance(axis_a_start, axis_b_start) <= EPS or distance(axis_a_end, axis_b_end) <= EPS:  # type: ignore[arg-type]
            return [], "关系轴两端在SHOT中重合，无法求解轴侧"
        samples.extend(
            quadratic_side_samples(
                camera_start,
                camera_end,
                axis_a_start,  # type: ignore[arg-type]
                axis_a_end,  # type: ignore[arg-type]
                axis_b_start,  # type: ignore[arg-type]
                axis_b_end,  # type: ignore[arg-type]
            )
        )
    return samples, None


def parse_scene_basis(
    basis: dict[str, Any],
    errors: list[str],
    error_codes: list[str],
) -> tuple[
    dict[str, tuple[float, float]],
    list[tuple[str, tuple[float, float, float], tuple[float, float, float]]],
    dict[str, dict[str, object]],
    dict[str, float],
    dict[str, dict[str, object]],
]:
    bounds_raw = basis.get("bounds_world") if isinstance(basis.get("bounds_world"), dict) else {}
    bounds: dict[str, tuple[float, float]] = {}
    for axis in ("x", "y", "z"):
        pair = bounds_raw.get(axis)
        if not isinstance(pair, list) or len(pair) != 2:
            add(errors, error_codes, "invalid_scene_space_basis", f"bounds_world.{axis}必须是[min,max]")
            continue
        low, high = as_float(pair[0]), as_float(pair[1])
        if low is None or high is None or low >= high:
            add(errors, error_codes, "invalid_scene_space_basis", f"bounds_world.{axis}范围无效")
            continue
        bounds[axis] = (low, high)

    for field in ("anchor_ids", "walkable_zone_ids"):
        value = basis.get(field)
        if not isinstance(value, list) or not value:
            add(errors, error_codes, "invalid_scene_space_basis", f"scene_space_basis.{field}必须是非空数组")
    if not isinstance(basis.get("locked_facts"), list):
        add(errors, error_codes, "invalid_scene_space_basis", "scene_space_basis.locked_facts必须是数组")

    obstacles: list[tuple[str, tuple[float, float, float], tuple[float, float, float]]] = []
    raw_obstacles = basis.get("blocked_volumes")
    if not isinstance(raw_obstacles, list):
        add(errors, error_codes, "invalid_scene_space_basis", "blocked_volumes必须是数组")
    else:
        for index, item in enumerate(raw_obstacles, start=1):
            if not isinstance(item, dict):
                add(errors, error_codes, "invalid_scene_space_basis", f"blocked_volumes[{index}]必须是对象")
                continue
            obstacle_id = text(item.get("obstacle_id"))
            minimum, maximum = vector(item.get("min_world")), vector(item.get("max_world"))
            if (
                not obstacle_id
                or minimum is None
                or maximum is None
                or any(minimum[i] >= maximum[i] for i in range(3))
            ):
                add(errors, error_codes, "invalid_scene_space_basis", f"blocked_volumes[{index}]字段无效")
                continue
            obstacles.append((obstacle_id, minimum, maximum))

    axes: dict[str, dict[str, object]] = {}
    raw_axes = basis.get("relationship_axes")
    if not isinstance(raw_axes, list):
        add(errors, error_codes, "invalid_scene_space_basis", "relationship_axes必须是数组；无关系轴时使用[]")
    else:
        for index, item in enumerate(raw_axes, start=1):
            if not isinstance(item, dict):
                add(errors, error_codes, "invalid_scene_space_basis", f"relationship_axes[{index}]必须是对象")
                continue
            axis_id = text(item.get("axis_id"))
            source_type = text(item.get("source_type") or "fixed")
            if not axis_id or axis_id in axes or source_type not in {"fixed", "actor_pair"}:
                add(errors, error_codes, "invalid_scene_space_basis", f"relationship_axes[{index}]编号或source_type无效")
                continue
            if source_type == "fixed":
                point_a, point_b = vector(item.get("point_a_world")), vector(item.get("point_b_world"))
                if point_a is None or point_b is None or distance(point_a, point_b) <= EPS:
                    add(errors, error_codes, "invalid_scene_space_basis", f"relationship_axes[{index}]固定轴字段无效")
                    continue
                axes[axis_id] = {"source_type": "fixed", "point_a": point_a, "point_b": point_b}
            else:
                actor_a_id, actor_b_id = text(item.get("actor_a_id")), text(item.get("actor_b_id"))
                if not actor_a_id or not actor_b_id or actor_a_id == actor_b_id:
                    add(errors, error_codes, "invalid_scene_space_basis", f"relationship_axes[{index}]人物关系轴字段无效")
                    continue
                axes[axis_id] = {
                    "source_type": "actor_pair",
                    "actor_a_id": actor_a_id,
                    "actor_b_id": actor_b_id,
                }

    camera_regions: set[str] = set()
    raw_regions = basis.get("camera_allowed_regions")
    if not isinstance(raw_regions, list) or not raw_regions:
        add(errors, error_codes, "invalid_scene_space_basis", "camera_allowed_regions必须是非空数组")
    else:
        for index, item in enumerate(raw_regions, start=1):
            if not isinstance(item, dict):
                add(errors, error_codes, "invalid_scene_space_basis", f"camera_allowed_regions[{index}]必须是对象")
                continue
            region_id = text(item.get("region_id"))
            if not region_id or region_id in camera_regions:
                add(errors, error_codes, "invalid_scene_space_basis", f"camera_allowed_regions[{index}].region_id为空或重复")
                continue
            camera_regions.add(region_id)

    camera_stations: dict[str, dict[str, object]] = {}
    raw_stations = basis.get("camera_station_candidates")
    if not isinstance(raw_stations, list) or not raw_stations:
        add(errors, error_codes, "invalid_scene_space_basis", "camera_station_candidates必须是非空数组")
    else:
        for index, item in enumerate(raw_stations, start=1):
            if not isinstance(item, dict):
                add(errors, error_codes, "invalid_scene_space_basis", f"camera_station_candidates[{index}]必须是对象")
                continue
            station_id = text(item.get("station_id"))
            region_id = text(item.get("region_id"))
            position = vector(item.get("position_world"))
            forward = vector(item.get("forward_world"))
            if not station_id or station_id in camera_stations:
                add(errors, error_codes, "invalid_scene_space_basis", f"camera_station_candidates[{index}].station_id为空或重复")
                continue
            if not region_id or region_id not in camera_regions:
                add(errors, error_codes, "invalid_scene_space_basis", f"camera_station_candidates[{index}].region_id无效")
                continue
            if position is None or forward is None or normalized(forward) is None:
                add(errors, error_codes, "invalid_scene_space_basis", f"camera_station_candidates[{index}]坐标或朝向无效")
                continue
            if bounds and not in_bounds(position, bounds):
                add(errors, error_codes, "invalid_scene_space_basis", f"camera_station_candidates[{index}]超出场景边界")
                continue
            camera_stations[station_id] = {
                "region_id": region_id,
                "position_world": position,
                "forward_world": forward,
                "height": position[2],
            }

    limits: dict[str, float] = {}
    for field in (
        "camera_clearance_units",
        "actor_clearance_units",
        "max_camera_speed_units_per_second",
        "max_actor_speed_units_per_second",
        "max_camera_angular_speed_degrees_per_second",
    ):
        value = as_float(basis.get(field))
        if value is None or value <= 0:
            add(errors, error_codes, "invalid_scene_space_basis", f"scene_space_basis.{field}必须大于0")
        else:
            limits[field] = value
    return bounds, obstacles, axes, limits, camera_stations


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("directorial_camera_plan"), dict):
        payload = payload["directorial_camera_plan"]

    errors: list[str] = []
    warnings: list[str] = []
    error_codes: list[str] = []
    warning_codes: list[str] = []

    if not isinstance(payload, dict):
        add(errors, error_codes, "invalid_plan", "输入必须是对象")
        return {
            "ok": False,
            "errors": errors,
            "error_codes": error_codes,
            "warnings": [],
            "warning_codes": [],
        }

    if has_legacy_mode_contract(payload):
        add(
            errors,
            error_codes,
            "stale_three_mode_contract",
            "不得再使用locked／movement／cut_to_new_shot三选一旧合同",
        )

    for field in ("plan_id", "segment_id", "scene_id"):
        if not text(payload.get(field)):
            add(errors, error_codes, "missing_plan_identity", f"{field}不能为空")
    content_type = text(payload.get("segment_content_type"))
    if content_type not in SEGMENT_CONTENT_TYPES:
        add(errors, error_codes, "invalid_segment_content_type", "segment_content_type无效")
    duration = as_float(payload.get("duration_seconds"))
    if duration is None or duration <= 0:
        duration = 0.0
        add(errors, error_codes, "invalid_duration_seconds", "duration_seconds必须大于0")

    read = payload.get("director_read") if isinstance(payload.get("director_read"), dict) else {}
    for field in DIRECTOR_READ_FIELDS:
        if not text(read.get(field)):
            add(errors, error_codes, "missing_director_read", f"director_read.{field}不能为空")
    if generic_reason(read.get("scene_intention")):
        add(errors, error_codes, "missing_director_read", "scene_intention不能只是电影感等空泛词")

    basis = payload.get("scene_space_basis") if isinstance(payload.get("scene_space_basis"), dict) else {}
    bounds, obstacles, relationship_axes, limits, camera_stations = parse_scene_basis(basis, errors, error_codes)

    scene_camera_grammar = payload.get("scene_camera_grammar") if isinstance(payload.get("scene_camera_grammar"), dict) else {}
    for field in ("dramatic_progression", "coverage_intent"):
        if not text(scene_camera_grammar.get(field)):
            add(errors, error_codes, "invalid_scene_camera_grammar", f"scene_camera_grammar.{field}不能为空")
    grammar_station_library = scene_camera_grammar.get("station_library")
    if not isinstance(grammar_station_library, list) or not grammar_station_library:
        add(errors, error_codes, "invalid_scene_camera_grammar", "scene_camera_grammar.station_library必须是非空数组")
        grammar_station_ids: set[str] = set()
    else:
        grammar_station_ids = {text(item) for item in grammar_station_library if text(item)}
        if len(grammar_station_ids) != len(grammar_station_library):
            add(errors, error_codes, "invalid_scene_camera_grammar", "scene_camera_grammar.station_library存在空值或重复")
        unknown = grammar_station_ids - set(camera_stations)
        if unknown:
            add(errors, error_codes, "invalid_scene_camera_grammar", f"station_library引用未知摄影点：{sorted(unknown)}")
    for field in ("planned_station_sequence", "shot_scale_curve", "psychological_distance_curve"):
        if not isinstance(scene_camera_grammar.get(field), list) or not scene_camera_grammar.get(field):
            add(errors, error_codes, "invalid_scene_camera_grammar", f"scene_camera_grammar.{field}必须是非空数组")

    beats_raw = payload.get("beats")
    beats = beats_raw if isinstance(beats_raw, list) else []
    if not beats:
        add(errors, error_codes, "invalid_beat_timeline", "beats必须是非空数组")
    beat_ids: set[str] = set()
    beat_ranges: dict[str, tuple[float, float]] = {}
    previous_beat_end = 0.0
    for index, beat in enumerate(beats, start=1):
        if not isinstance(beat, dict):
            add(errors, error_codes, "invalid_beat_timeline", f"beats[{index}]必须是对象")
            continue
        beat_id = text(beat.get("beat_id"))
        if not beat_id or beat_id in beat_ids:
            add(errors, error_codes, "invalid_beat_timeline", f"beats[{index}]编号为空或重复")
        beat_ids.add(beat_id)
        start, end = as_float(beat.get("start_seconds")), as_float(beat.get("end_seconds"))
        if start is None or end is None or start < -EPS or end <= start or (duration and end > duration + EPS):
            add(errors, error_codes, "invalid_beat_timeline", f"beat {beat_id or index}时间范围无效")
            start, end = previous_beat_end, previous_beat_end
        if abs(start - previous_beat_end) > EPS:
            add(errors, error_codes, "invalid_beat_timeline", f"beat {beat_id or index}与前一节拍存在空隙或重叠")
        previous_beat_end = end
        beat_ranges[beat_id] = (start, end)
        for field in ("dramatic_task", "primary_subject_id"):
            if not text(beat.get(field)):
                add(errors, error_codes, "invalid_beat_timeline", f"beat {beat_id or index}缺少{field}")
        evidence = beat.get("required_visible_evidence")
        if not isinstance(evidence, list) or not evidence:
            add(errors, error_codes, "invalid_beat_timeline", f"beat {beat_id or index}缺少required_visible_evidence")
    if duration and abs(previous_beat_end - duration) > EPS:
        add(errors, error_codes, "invalid_beat_timeline", "视觉节拍必须完整覆盖duration_seconds")

    shots_raw = payload.get("shots")
    shots = shots_raw if isinstance(shots_raw, list) else []
    if not shots:
        add(errors, error_codes, "invalid_shot_timeline", "shots必须是非空数组")
    planned_shot_ids = [text(item.get("shot_id")) if isinstance(item, dict) else "" for item in shots]
    seen_shot_ids: set[str] = set()
    shot_ranges: dict[str, tuple[float, float]] = {}
    shot_actor_ids: dict[str, set[str]] = {}
    shot_station_ids: dict[str, str] = {}
    shot_observation_signatures: dict[str, dict[str, object]] = {}
    shot_inheritance_flags: dict[str, bool] = {}
    previous_end = 0.0
    for index, shot in enumerate(shots):
        ordinal = index + 1
        if not isinstance(shot, dict):
            add(errors, error_codes, "invalid_shot_timeline", f"shots[{ordinal}]必须是对象")
            continue
        shot_id = planned_shot_ids[index]
        if not shot_id or shot_id in seen_shot_ids:
            add(errors, error_codes, "invalid_shot_timeline", f"shots[{ordinal}]编号为空或重复")
        seen_shot_ids.add(shot_id)
        start, end = as_float(shot.get("start_seconds")), as_float(shot.get("end_seconds"))
        if start is None or end is None or end <= start:
            add(errors, error_codes, "invalid_shot_timeline", f"SHOT {shot_id or ordinal}时间范围无效")
            start, end = previous_end, previous_end
        if abs(start - previous_end) > EPS:
            add(errors, error_codes, "invalid_shot_timeline", f"SHOT {shot_id or ordinal}与前一SHOT存在空隙或重叠")
        previous_end = end
        shot_ranges[shot_id] = (start, end)
        for field in ("dramatic_task", "primary_subject_id"):
            if not text(shot.get(field)):
                add(errors, error_codes, "invalid_shot_timeline", f"SHOT {shot_id or ordinal}缺少{field}")
        refs = shot.get("beat_ids")
        if not isinstance(refs, list) or not refs or any(text(item) not in beat_ids for item in refs):
            add(errors, error_codes, "invalid_shot_timeline", f"SHOT {shot_id or ordinal}的beat_ids无效")
            refs = []
        actor_ids_raw = shot.get("actor_ids")
        if not isinstance(actor_ids_raw, list) or any(not text(item) for item in actor_ids_raw):
            add(errors, error_codes, "invalid_shot_timeline", f"SHOT {shot_id or ordinal}.actor_ids必须是字符串数组；无人镜头使用[]")
            actor_ids_raw = []
        actor_ids = [text(item) for item in actor_ids_raw]
        if len(set(actor_ids)) != len(actor_ids):
            add(errors, error_codes, "invalid_shot_timeline", f"SHOT {shot_id or ordinal}.actor_ids不得重复")
        shot_actor_ids[shot_id] = set(actor_ids)

        camera_station_id = text(shot.get("camera_station_id"))
        if not camera_station_id or camera_station_id not in camera_stations:
            add(errors, error_codes, "invalid_camera_station", f"SHOT {shot_id or ordinal}.camera_station_id缺失或不在04A摄影点库")
        shot_station_ids[shot_id] = camera_station_id
        lock = shot.get("shot_solution_lock") if isinstance(shot.get("shot_solution_lock"), dict) else {}
        if text(lock.get("scope")) != "shot":
            add(errors, error_codes, "invalid_solution_lock_scope", f"SHOT {shot_id or ordinal}方案锁只能作用于当前SHOT")
        if text(lock.get("locked_camera_station_id")) != camera_station_id:
            add(errors, error_codes, "invalid_solution_lock_scope", f"SHOT {shot_id or ordinal}锁定摄影点必须与camera_station_id一致")
        inherited = shot.get("camera_station_inherited_from_previous")
        if not isinstance(inherited, bool):
            add(errors, error_codes, "invalid_camera_inheritance_contract", f"SHOT {shot_id or ordinal}.camera_station_inherited_from_previous必须为布尔值")
            inherited = False
        shot_inheritance_flags[shot_id] = inherited
        signature = shot.get("observation_signature") if isinstance(shot.get("observation_signature"), dict) else {}
        for field in (
            "camera_region_id", "shot_scale", "foreground_subject_id",
            "background_anchor_id", "viewpoint_type", "motion_mode",
            "psychological_distance",
        ):
            if not text(signature.get(field)):
                add(errors, error_codes, "invalid_observation_signature", f"SHOT {shot_id or ordinal}.observation_signature.{field}不能为空")
        if camera_station_id in camera_stations and text(signature.get("camera_region_id")) != text(camera_stations[camera_station_id].get("region_id")):
            add(errors, error_codes, "invalid_observation_signature", f"SHOT {shot_id or ordinal}观察签名的camera_region_id与摄影点库不一致")
        shot_observation_signatures[shot_id] = signature

        intent = shot.get("camera_trajectory_intent") if isinstance(shot.get("camera_trajectory_intent"), dict) else {}
        for field in TRAJECTORY_FIELDS:
            value = intent.get(field)
            if field == "required_action_visibility":
                if not isinstance(value, list):
                    add(errors, error_codes, "missing_camera_trajectory_intent", f"SHOT {shot_id or ordinal}.{field}必须是数组")
            elif field == "hold_after_arrival_seconds":
                hold = as_float(value)
                if hold is None or hold < 0 or (end > start and hold > end - start + EPS):
                    add(errors, error_codes, "missing_camera_trajectory_intent", f"SHOT {shot_id or ordinal}.{field}无效")
            elif not text(value):
                add(errors, error_codes, "missing_camera_trajectory_intent", f"SHOT {shot_id or ordinal}.{field}不能为空")
        if generic_reason(intent.get("movement_purpose")):
            add(errors, error_codes, "unmotivated_camera_trajectory", f"SHOT {shot_id or ordinal}的摄影机轨迹目的不能只是电影感")

        cut = shot.get("cut_out_intent")
        if not isinstance(cut, dict) or not isinstance(cut.get("enabled"), bool):
            add(errors, error_codes, "missing_cut_intent", f"SHOT {shot_id or ordinal}必须显式提供cut_out_intent.enabled")
            cut = {}
        if index < len(shots) - 1:
            if cut.get("enabled") is not True:
                add(errors, error_codes, "missing_cut_intent", f"非末尾SHOT {shot_id or ordinal}必须显式设计CUT")
            else:
                at = as_float(cut.get("at_seconds"))
                next_id = planned_shot_ids[index + 1]
                if at is None or abs(at - end) > EPS or text(cut.get("next_shot_id")) != next_id:
                    add(errors, error_codes, "cut_sequence_mismatch", f"SHOT {shot_id or ordinal}的CUT时间或next_shot_id不匹配")
                cut_beat = text(cut.get("cut_point_beat_id"))
                if cut_beat not in beat_ids or cut_beat not in {text(item) for item in refs}:
                    add(errors, error_codes, "cut_sequence_mismatch", f"SHOT {shot_id or ordinal}的cut_point_beat_id必须属于当前SHOT")
                if text(cut.get("cut_type_intent")) not in CUT_TYPE_INTENTS:
                    add(errors, error_codes, "invalid_cut_type_intent", f"SHOT {shot_id or ordinal}必须由导演层提出合法cut_type_intent")
                if text(cut.get("transition_mechanism")) not in CUT_MECHANISMS:
                    add(errors, error_codes, "invalid_cut_transition_mechanism", f"SHOT {shot_id or ordinal}必须说明CUT如何发生")
                if generic_reason(cut.get("reason")):
                    add(errors, error_codes, "unmotivated_cut", f"SHOT {shot_id or ordinal}的CUT理由不能为空或只写节奏／电影感")
        elif cut.get("enabled") is True:
            add(errors, error_codes, "cut_sequence_mismatch", "末尾SHOT不能指向不存在的下一SHOT")

    if duration and abs(previous_end - duration) > EPS:
        add(errors, error_codes, "invalid_shot_timeline", "SHOT时间轴必须完整覆盖duration_seconds")

    planned_station_sequence = [text(item) for item in scene_camera_grammar.get("planned_station_sequence", [])] if isinstance(scene_camera_grammar.get("planned_station_sequence"), list) else []
    actual_station_sequence = [shot_station_ids.get(shot_id, "") for shot_id in planned_shot_ids]
    if planned_station_sequence != actual_station_sequence:
        add(errors, error_codes, "invalid_scene_camera_grammar", "planned_station_sequence必须与SHOT camera_station_id顺序一致")
    shot_scale_curve = [text(item) for item in scene_camera_grammar.get("shot_scale_curve", [])] if isinstance(scene_camera_grammar.get("shot_scale_curve"), list) else []
    actual_scale_curve = [text(shot_observation_signatures.get(shot_id, {}).get("shot_scale")) for shot_id in planned_shot_ids]
    if shot_scale_curve != actual_scale_curve:
        add(errors, error_codes, "invalid_scene_camera_grammar", "shot_scale_curve必须与SHOT观察签名一致")
    psychological_curve = [text(item) for item in scene_camera_grammar.get("psychological_distance_curve", [])] if isinstance(scene_camera_grammar.get("psychological_distance_curve"), list) else []
    actual_psychological_curve = [text(shot_observation_signatures.get(shot_id, {}).get("psychological_distance")) for shot_id in planned_shot_ids]
    if psychological_curve != actual_psychological_curve:
        add(errors, error_codes, "invalid_scene_camera_grammar", "psychological_distance_curve必须与SHOT观察签名一致")

    solution = payload.get("spatial_solution") if isinstance(payload.get("spatial_solution"), dict) else {}
    status = text(solution.get("status"))
    if status == "return_to_director_plan":
        if not isinstance(solution.get("failure_codes"), list) or not solution.get("failure_codes"):
            add(errors, error_codes, "spatial_plan_requires_redesign", "空间失败必须给出failure_codes")
        if not isinstance(solution.get("redesign_constraints"), list) or not solution.get("redesign_constraints"):
            add(errors, error_codes, "spatial_plan_requires_redesign", "空间失败必须给出redesign_constraints")
        add(errors, error_codes, "spatial_plan_requires_redesign", "当前导演方案无法空间落地，必须返回15重做")
    elif status != "solved":
        add(errors, error_codes, "invalid_spatial_solution", "spatial_solution.status必须为solved或return_to_director_plan")

    derived_behaviors: list[dict[str, object]] = []
    derived_spatial_checks: list[dict[str, object]] = []
    coverage_shots: list[dict[str, object]] = []
    spatial_error_codes = {
        "camera_position_out_of_bounds", "actor_position_out_of_bounds",
        "camera_path_intersects_obstacle", "actor_path_intersects_obstacle",
        "camera_path_intersects_subject", "camera_path_crosses_axis",
        "camera_speed_exceeds_space_limit", "camera_angular_speed_exceeds_space_limit",
        "actor_speed_exceeds_space_limit", "camera_keyframe_timeline_error",
        "actor_keyframe_timeline_error", "missing_actor_spatial_solution",
        "unknown_relationship_axis", "axis_policy_mismatch",
    }

    if status == "solved":
        solutions_raw = solution.get("shot_solutions")
        solutions = solutions_raw if isinstance(solutions_raw, list) else []
        by_id = {
            text(item.get("shot_id")): item
            for item in solutions
            if isinstance(item, dict) and text(item.get("shot_id"))
        }
        if set(by_id) != set(planned_shot_ids):
            add(errors, error_codes, "spatial_solution_shot_mismatch", "shot_solutions必须与导演SHOT一一对应")

        for shot_index, shot in enumerate(shots):
            if not isinstance(shot, dict):
                continue
            shot_id = planned_shot_ids[shot_index]
            solved = by_id.get(shot_id, {})
            if text(solved.get("camera_station_id")) != shot_station_ids.get(shot_id, ""):
                add(errors, error_codes, "spatial_solution_station_mismatch", f"SHOT {shot_id}空间解camera_station_id与导演方案不一致")
            start, end = shot_ranges.get(shot_id, (0.0, 0.0))
            before_codes = len(error_codes)

            frames_raw = solved.get("camera_keyframes")
            frames = frames_raw if isinstance(frames_raw, list) else []
            parsed_frames: list[dict[str, object]] = []
            last_time: float | None = None
            for frame_index, frame in enumerate(frames, start=1):
                if not isinstance(frame, dict):
                    add(errors, error_codes, "camera_keyframe_timeline_error", f"SHOT {shot_id}关键帧{frame_index}必须是对象")
                    continue
                time_value = as_float(frame.get("time_seconds"))
                position = vector(frame.get("position_world"))
                forward = vector(frame.get("forward_world"))
                if (
                    time_value is None
                    or position is None
                    or forward is None
                    or normalized(forward) is None
                    or not text(frame.get("framing"))
                ):
                    add(errors, error_codes, "camera_keyframe_timeline_error", f"SHOT {shot_id}关键帧{frame_index}字段无效")
                    continue
                if last_time is not None and time_value <= last_time + EPS:
                    add(errors, error_codes, "camera_keyframe_timeline_error", f"SHOT {shot_id}关键帧时间必须严格递增")
                last_time = time_value
                if not in_bounds(position, bounds):
                    add(errors, error_codes, "camera_position_out_of_bounds", f"SHOT {shot_id}关键帧{frame_index}超出场景边界")
                parsed_frames.append({**frame, "_time": time_value, "_position": position, "_forward": forward})
            if len(parsed_frames) < 2:
                add(errors, error_codes, "camera_keyframe_timeline_error", f"SHOT {shot_id}至少需要起点和终点关键帧")
                continue
            if (
                abs(float(parsed_frames[0]["_time"]) - start) > EPS
                or abs(float(parsed_frames[-1]["_time"]) - end) > EPS
            ):
                add(errors, error_codes, "camera_keyframe_timeline_error", f"SHOT {shot_id}关键帧必须覆盖完整SHOT起止时间")

            actor_frames_raw = solved.get("actor_keyframes")
            actor_frames = actor_frames_raw if isinstance(actor_frames_raw, list) else []
            actor_tracks: dict[str, list[dict[str, object]]] = {}
            expected_actor_ids = shot_actor_ids.get(shot_id, set())
            if expected_actor_ids and not actor_frames:
                add(errors, error_codes, "missing_actor_spatial_solution", f"SHOT {shot_id}缺少人物XYZ关键帧")
            for actor_index, actor in enumerate(actor_frames, start=1):
                if not isinstance(actor, dict):
                    add(errors, error_codes, "missing_actor_spatial_solution", f"SHOT {shot_id}人物关键帧{actor_index}必须是对象")
                    continue
                actor_id = text(actor.get("actor_id"))
                time_value = as_float(actor.get("time_seconds"))
                position = vector(actor.get("position_world"))
                forward = vector(actor.get("body_forward_world"))
                if not actor_id or time_value is None or position is None or forward is None or normalized(forward) is None:
                    add(errors, error_codes, "missing_actor_spatial_solution", f"SHOT {shot_id}人物关键帧{actor_index}字段无效")
                    continue
                if time_value < start - EPS or time_value > end + EPS:
                    add(errors, error_codes, "actor_keyframe_timeline_error", f"SHOT {shot_id}人物关键帧{actor_index}不在SHOT时间范围")
                if not in_bounds(position, bounds):
                    add(errors, error_codes, "actor_position_out_of_bounds", f"SHOT {shot_id}人物{actor_id}超出场景边界")
                actor_tracks.setdefault(actor_id, []).append({
                    **actor,
                    "_time": time_value,
                    "_position": position,
                    "_forward": forward,
                })
            if set(actor_tracks) != expected_actor_ids:
                add(
                    errors,
                    error_codes,
                    "missing_actor_spatial_solution",
                    f"SHOT {shot_id}人物轨迹集合{sorted(actor_tracks)}与actor_ids{sorted(expected_actor_ids)}不一致",
                )
            for actor_id, track in actor_tracks.items():
                track.sort(key=lambda item: float(item["_time"]))
                if (
                    abs(float(track[0]["_time"]) - start) > EPS
                    or abs(float(track[-1]["_time"]) - end) > EPS
                ):
                    add(errors, error_codes, "actor_keyframe_timeline_error", f"SHOT {shot_id}人物{actor_id}轨迹必须覆盖完整SHOT")
                for index in range(1, len(track)):
                    dt = float(track[index]["_time"]) - float(track[index - 1]["_time"])
                    if dt <= EPS:
                        add(errors, error_codes, "actor_keyframe_timeline_error", f"SHOT {shot_id}人物{actor_id}时间必须严格递增")
                        continue
                    actor_start = track[index - 1]["_position"]  # type: ignore[assignment]
                    actor_end = track[index]["_position"]  # type: ignore[assignment]
                    speed = distance(actor_start, actor_end) / dt
                    if speed > limits.get("max_actor_speed_units_per_second", float("inf")) + EPS:
                        add(errors, error_codes, "actor_speed_exceeds_space_limit", f"SHOT {shot_id}人物{actor_id}速度超过空间上限")
                    for obstacle_id, minimum, maximum in obstacles:
                        if segment_intersects_aabb(
                            actor_start,
                            actor_end,
                            minimum,
                            maximum,
                            limits.get("actor_clearance_units", 0.0),
                        ):
                            add(errors, error_codes, "actor_path_intersects_obstacle", f"SHOT {shot_id}人物{actor_id}轨迹与障碍{obstacle_id}相交")

            actual_obstacle_hit = False
            actual_subject_hit = False
            for index in range(1, len(parsed_frames)):
                left, right = parsed_frames[index - 1], parsed_frames[index]
                left_t, right_t = float(left["_time"]), float(right["_time"])
                dt = right_t - left_t
                camera_start = left["_position"]  # type: ignore[assignment]
                camera_end = right["_position"]  # type: ignore[assignment]
                if dt <= EPS:
                    add(errors, error_codes, "camera_keyframe_timeline_error", f"SHOT {shot_id}摄影机时间必须严格递增")
                    continue
                camera_speed = distance(camera_start, camera_end) / dt
                if camera_speed > limits.get("max_camera_speed_units_per_second", float("inf")) + EPS:
                    add(errors, error_codes, "camera_speed_exceeds_space_limit", f"SHOT {shot_id}摄影机速度超过空间上限")
                angular_speed = angle_degrees(left["_forward"], right["_forward"]) / dt  # type: ignore[arg-type]
                if angular_speed > limits.get("max_camera_angular_speed_degrees_per_second", float("inf")) + EPS:
                    add(errors, error_codes, "camera_angular_speed_exceeds_space_limit", f"SHOT {shot_id}摄影机转向速度超过空间上限")
                for obstacle_id, minimum, maximum in obstacles:
                    if segment_intersects_aabb(
                        camera_start,
                        camera_end,
                        minimum,
                        maximum,
                        limits.get("camera_clearance_units", 0.0),
                    ):
                        actual_obstacle_hit = True
                        add(errors, error_codes, "camera_path_intersects_obstacle", f"SHOT {shot_id}XYZ轨迹与障碍{obstacle_id}相交")

                for actor_id, track in actor_tracks.items():
                    for actor_index in range(1, len(track)):
                        actor_left, actor_right = track[actor_index - 1], track[actor_index]
                        overlap = track_overlaps(
                            left_t,
                            right_t,
                            float(actor_left["_time"]),
                            float(actor_right["_time"]),
                        )
                        if overlap is None:
                            continue
                        overlap_start, overlap_end = overlap
                        camera_overlap_start = lerp(camera_start, camera_end, (overlap_start - left_t) / dt)
                        camera_overlap_end = lerp(camera_start, camera_end, (overlap_end - left_t) / dt)
                        actor_dt = float(actor_right["_time"]) - float(actor_left["_time"])
                        if actor_dt <= EPS:
                            continue
                        actor_overlap_start = lerp(
                            actor_left["_position"],  # type: ignore[arg-type]
                            actor_right["_position"],  # type: ignore[arg-type]
                            (overlap_start - float(actor_left["_time"])) / actor_dt,
                        )
                        actor_overlap_end = lerp(
                            actor_left["_position"],  # type: ignore[arg-type]
                            actor_right["_position"],  # type: ignore[arg-type]
                            (overlap_end - float(actor_left["_time"])) / actor_dt,
                        )
                        if minimum_synchronous_distance(
                            camera_overlap_start,
                            camera_overlap_end,
                            actor_overlap_start,
                            actor_overlap_end,
                        ) < limits.get("actor_clearance_units", 0.0) - EPS:
                            actual_subject_hit = True
                            add(errors, error_codes, "camera_path_intersects_subject", f"SHOT {shot_id}摄影机与人物{actor_id}动态轨迹距离不足")
                            break
                    if actual_subject_hit:
                        break

            axis_policy = text(solved.get("axis_policy"))
            if axis_policy not in AXIS_POLICIES:
                add(errors, error_codes, "axis_policy_mismatch", f"SHOT {shot_id}.axis_policy必须为preserve、visible_reestablish或not_applicable")
                axis_policy = ""
            actual_cross = False
            axis_id = text(solved.get("relationship_axis_id"))
            if axis_policy == "not_applicable":
                if axis_id:
                    add(warnings, warning_codes, "unused_relationship_axis", f"SHOT {shot_id}标记轴线不适用但仍提供relationship_axis_id")
            elif axis_policy:
                axis = relationship_axes.get(axis_id)
                if axis is None:
                    add(errors, error_codes, "unknown_relationship_axis", f"SHOT {shot_id}缺少合法relationship_axis_id")
                else:
                    signs, axis_error = relationship_axis_side_samples(axis, parsed_frames, actor_tracks)
                    if axis_error:
                        add(errors, error_codes, "unknown_relationship_axis", f"SHOT {shot_id}{axis_error}")
                    else:
                        actual_cross = any(value > EPS for value in signs) and any(value < -EPS for value in signs)
                        if axis_policy == "preserve" and actual_cross:
                            add(errors, error_codes, "camera_path_crosses_axis", f"SHOT {shot_id}导演要求保持轴侧，但XYZ轨迹实际跨轴")
                        if axis_policy == "visible_reestablish":
                            evidence = solved.get("axis_reestablishment_evidence")
                            if not actual_cross or not isinstance(evidence, list) or not evidence:
                                add(errors, error_codes, "axis_policy_mismatch", f"SHOT {shot_id}可见重建轴线必须有实际跨越与画面证据")

            moved = any(
                distance(parsed_frames[index - 1]["_position"], parsed_frames[index]["_position"]) > EPS  # type: ignore[arg-type]
                or direction_changed(parsed_frames[index - 1]["_forward"], parsed_frames[index]["_forward"])  # type: ignore[arg-type]
                for index in range(1, len(parsed_frames))
            )
            motion_axes: set[str] = set()
            orientation_changed = False
            for index in range(1, len(parsed_frames)):
                left, right = parsed_frames[index - 1], parsed_frames[index]
                for axis_index, axis_name in enumerate(("X", "Y", "Z")):
                    if abs(right["_position"][axis_index] - left["_position"][axis_index]) > EPS:  # type: ignore[index]
                        motion_axes.add(axis_name)
                if direction_changed(left["_forward"], right["_forward"]):  # type: ignore[arg-type]
                    orientation_changed = True
            if orientation_changed:
                motion_axes.add("PAN_TILT")
            if content_type != "high_speed_action" and len(motion_axes) > 2:
                add(errors, error_codes, "too_many_camera_motion_axes", f"SHOT {shot_id}普通SEG同时变化超过两个摄影机轴：{sorted(motion_axes)}")

            behavior = "continuous_motion" if moved else "locked"
            intent = shot.get("camera_trajectory_intent") if isinstance(shot.get("camera_trajectory_intent"), dict) else {}
            path_intent = text(intent.get("path_intent"))
            if intended_hold(path_intent) and moved:
                add(errors, error_codes, "camera_intent_solution_mismatch", f"SHOT {shot_id}导演要求固定，但空间解发生移动")
            if intended_move(path_intent) and not moved:
                add(errors, error_codes, "camera_intent_solution_mismatch", f"SHOT {shot_id}导演要求运镜，但空间解保持不动")

            hold = as_float(intent.get("hold_after_arrival_seconds")) or 0.0
            solved_hold = 0.0
            if hold > EPS:
                stationary_start = float(parsed_frames[-1]["_time"])
                for index in range(len(parsed_frames) - 2, -1, -1):
                    if state_equal(parsed_frames[index], parsed_frames[-1]):
                        stationary_start = float(parsed_frames[index]["_time"])
                    else:
                        break
                solved_hold = float(parsed_frames[-1]["_time"]) - stationary_start
                if solved_hold + EPS < hold:
                    add(errors, error_codes, "hold_duration_not_solved", f"SHOT {shot_id}终点锁定时长没有被XYZ关键帧实际实现")

            # Optional legacy claims are accepted only as assertions and must match derived geometry.
            if "intersects_obstacle" in solved and bool(solved.get("intersects_obstacle")) != actual_obstacle_hit:
                add(errors, error_codes, "spatial_solution_flag_mismatch", f"SHOT {shot_id}.intersects_obstacle与XYZ计算不一致")
            if "intersects_subject" in solved and bool(solved.get("intersects_subject")) != actual_subject_hit:
                add(errors, error_codes, "spatial_solution_flag_mismatch", f"SHOT {shot_id}.intersects_subject与XYZ计算不一致")
            if "path_clear" in solved and bool(solved.get("path_clear")) == (actual_obstacle_hit or actual_subject_hit):
                add(errors, error_codes, "spatial_solution_flag_mismatch", f"SHOT {shot_id}.path_clear与XYZ计算不一致")

            shot_new_codes = set(error_codes[before_codes:])
            shot_spatial_ok = not bool(shot_new_codes & spatial_error_codes)
            derived_behaviors.append({
                "shot_id": shot_id,
                "camera_behavior": behavior,
                "motion_axes": sorted(motion_axes),
                "solved_hold_seconds": solved_hold,
                "cut_after": shot_index < len(shots) - 1,
            })
            derived_spatial_checks.append({
                "shot_id": shot_id,
                "spatially_executable": shot_spatial_ok,
                "path_clear": not actual_obstacle_hit and not actual_subject_hit,
                "camera_intersects_obstacle": actual_obstacle_hit,
                "camera_intersects_subject": actual_subject_hit,
                "axis_policy": axis_policy,
                "axis_crossed": actual_cross,
            })
            signature = shot_observation_signatures.get(shot_id, {})
            coverage_shots.append({
                "shot_id": shot_id,
                "solution_lock_scope": "shot",
                "camera_station_id": shot_station_ids.get(shot_id, ""),
                "camera_region_id": text(signature.get("camera_region_id")),
                "camera_position_world": list(parsed_frames[0]["_position"]),
                "camera_forward_world": list(parsed_frames[0]["_forward"]),
                "camera_height": float(parsed_frames[0]["_position"][2]),
                "shot_scale": text(signature.get("shot_scale")),
                "primary_subject_id": text(shot.get("primary_subject_id")),
                "foreground_subject_id": text(signature.get("foreground_subject_id")),
                "background_anchor_id": text(signature.get("background_anchor_id")),
                "viewpoint_type": text(signature.get("viewpoint_type")),
                "motion_mode": text(signature.get("motion_mode")),
                "psychological_distance": text(signature.get("psychological_distance")),
                "camera_station_inherited_from_previous": shot_inheritance_flags.get(shot_id, False),
                "repetition_intent": text(shot.get("repetition_intent")),
                "repetition_payoff": text(shot.get("repetition_payoff")),
            })

    coverage_result = COVERAGE_VALIDATOR.validate({
        "scene_id": text(payload.get("scene_id")),
        "window_size": 3,
        "shots": coverage_shots,
    }) if coverage_shots else {"ok": False, "errors": ["invalid_camera_coverage: 缺少可验证SHOT"], "error_codes": ["invalid_camera_coverage"], "warnings": [], "warning_codes": []}
    for message, code in zip(coverage_result.get("errors", []), coverage_result.get("error_codes", [])):
        add(errors, error_codes, code, message.split(": ", 1)[-1])
    for message, code in zip(coverage_result.get("warnings", []), coverage_result.get("warning_codes", [])):
        add(warnings, warning_codes, code, message.split(": ", 1)[-1])

    return {
        "ok": not errors,
        "plan_id": text(payload.get("plan_id")),
        "segment_id": text(payload.get("segment_id")),
        "derived_shot_count": len(shots),
        "derived_cut_count": max(0, len(shots) - 1),
        "derived_behaviors": derived_behaviors,
        "derived_spatial_checks": derived_spatial_checks,
        "camera_coverage_validation": coverage_result,
        "requires_director_redesign": status == "return_to_director_plan" or any(
            code in spatial_error_codes for code in error_codes
        ),
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
        result = {
            "ok": False,
            "errors": [f"invalid_json: {exc}"],
            "error_codes": ["invalid_json"],
            "warnings": [],
            "warning_codes": [],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

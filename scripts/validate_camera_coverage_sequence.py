#!/usr/bin/env python3
"""Validate scene-level camera coverage and reject repeated one-view coverage.

This validator intentionally does not use a fixed camera-angle threshold. It compares
camera-station identity and a multi-field observation signature across a rolling
window. Repeated medium shots are valid when they come from meaningfully distinct
stations or observation relationships; repeated copies of the same station,
height, foreground, background and perspective are rejected unless repetition is
explicitly motivated and paid off.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

EPS = 1e-9
SCALE_LEVELS = {
    "EWS": 0, "EXTREME_WIDE": 0, "大远景": 0,
    "WS": 1, "WIDE": 1, "远景": 1, "全景": 1,
    "MWS": 2, "MEDIUM_WIDE": 2, "MLS": 2, "MEDIUM_LONG_SHOT": 2,
    "中远景": 2, "中全景": 2,
    "MS": 3, "MEDIUM": 3, "MEDIUM_SHOT": 3, "中景": 3,
    "MCU": 4, "MEDIUM_CLOSE": 4, "MEDIUM_CLOSE_UP": 4,
    "中近景": 4, "近景": 4,
    "CU": 5, "CLOSE": 5, "CLOSE_UP": 5, "特写": 5,
    "BCU": 6, "BIG_CLOSE": 6, "大特写": 6,
    "ECU": 7, "EXTREME_CLOSE": 7, "EXTREME_CLOSE_UP": 7,
    "极近特写": 7, "眼部极近特写": 7,
}


def load_payload(path: str | None) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8")) if path else json.load(sys.stdin)
    if isinstance(raw, dict) and isinstance(raw.get("scene_camera_coverage"), dict):
        return raw["scene_camera_coverage"]
    return raw


def text(value: object) -> str:
    return str(value or "").strip()


def number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def vector(value: object) -> tuple[float, float, float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    values = [number(item) for item in value]
    if any(item is None for item in values):
        return None
    return float(values[0]), float(values[1]), float(values[2])


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def direction_similarity(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    ma = math.sqrt(sum(x * x for x in a))
    mb = math.sqrt(sum(x * x for x in b))
    if ma <= EPS or mb <= EPS:
        return -1.0
    return sum(x * y for x, y in zip(a, b)) / (ma * mb)


def scale_level(value: object) -> int | None:
    key = text(value)
    return SCALE_LEVELS.get(key, SCALE_LEVELS.get(key.upper()))


def motivated(shot: dict[str, Any]) -> bool:
    return bool(text(shot.get("repetition_intent")) and text(shot.get("repetition_payoff")))


def same_or_adjacent_scale(a: dict[str, Any], b: dict[str, Any]) -> bool:
    first, second = scale_level(a.get("shot_scale")), scale_level(b.get("shot_scale"))
    if first is None or second is None:
        return text(a.get("shot_scale")) == text(b.get("shot_scale"))
    return abs(first - second) <= 1


def near_equivalent(a: dict[str, Any], b: dict[str, Any]) -> tuple[bool, list[str]]:
    pa, pb = vector(a.get("camera_position_world")), vector(b.get("camera_position_world"))
    fa, fb = vector(a.get("camera_forward_world")), vector(b.get("camera_forward_world"))
    height_a, height_b = number(a.get("camera_height")), number(b.get("camera_height"))

    equal_dimensions: list[str] = []
    if text(a.get("camera_station_id")) == text(b.get("camera_station_id")):
        equal_dimensions.append("camera_station_id")
    if text(a.get("camera_region_id")) == text(b.get("camera_region_id")):
        equal_dimensions.append("camera_region_id")
    if pa is not None and pb is not None and distance(pa, pb) <= 0.25:
        equal_dimensions.append("camera_position_world")
    if fa is not None and fb is not None and direction_similarity(fa, fb) >= 0.985:
        equal_dimensions.append("camera_forward_world")
    if height_a is not None and height_b is not None and abs(height_a - height_b) <= 0.1:
        equal_dimensions.append("camera_height")
    if same_or_adjacent_scale(a, b):
        equal_dimensions.append("shot_scale")
    for field in (
        "foreground_subject_id", "background_anchor_id", "viewpoint_type",
        "motion_mode", "psychological_distance",
    ):
        if text(a.get(field)) == text(b.get(field)):
            equal_dimensions.append(field)

    # Primary subject is deliberately excluded. Merely swapping the speaker or
    # central subject must not make a repeated camera setup look different.
    core = {
        "camera_position_world", "camera_forward_world", "camera_height",
        "shot_scale", "foreground_subject_id", "background_anchor_id",
        "viewpoint_type", "motion_mode", "psychological_distance",
    }
    near = len(core.intersection(equal_dimensions)) >= 7
    return near, equal_dimensions


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    error_codes: list[str] = []
    warning_codes: list[str] = []

    def add_error(code: str, message: str) -> None:
        errors.append(f"{code}: {message}")
        error_codes.append(code)

    def add_warning(code: str, message: str) -> None:
        warnings.append(f"{code}: {message}")
        warning_codes.append(code)

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "errors": ["invalid_camera_coverage: 输入必须是对象"],
            "error_codes": ["invalid_camera_coverage"],
            "warnings": [],
            "warning_codes": [],
        }

    scene_id = text(payload.get("scene_id"))
    if not scene_id:
        add_error("invalid_camera_coverage", "scene_id不能为空")

    window_size_raw = payload.get("window_size", 3)
    try:
        window_size = int(window_size_raw)
    except (TypeError, ValueError):
        window_size = 3
        add_error("invalid_camera_coverage", "window_size必须是整数")
    if window_size < 3:
        add_error("invalid_camera_coverage", "window_size不得小于3")
        window_size = 3

    shots_raw = payload.get("shots")
    shots = shots_raw if isinstance(shots_raw, list) else []
    if not shots:
        add_error("invalid_camera_coverage", "shots必须是非空数组")

    required_text_fields = (
        "shot_id", "camera_station_id", "camera_region_id", "shot_scale",
        "primary_subject_id", "foreground_subject_id", "background_anchor_id",
        "viewpoint_type", "motion_mode", "psychological_distance",
    )
    seen_ids: set[str] = set()
    parsed: list[dict[str, Any]] = []
    for index, raw in enumerate(shots, start=1):
        if not isinstance(raw, dict):
            add_error("invalid_camera_coverage", f"shots[{index}]必须是对象")
            continue
        shot = dict(raw)
        shot_id = text(shot.get("shot_id"))
        if not shot_id or shot_id in seen_ids:
            add_error("invalid_camera_coverage", f"shots[{index}].shot_id为空或重复")
        seen_ids.add(shot_id)
        for field in required_text_fields:
            if not text(shot.get(field)):
                add_error("invalid_observation_signature", f"SHOT {shot_id or index}.{field}不能为空")
        if text(shot.get("solution_lock_scope")) != "shot":
            add_error(
                "invalid_solution_lock_scope",
                f"SHOT {shot_id or index}的方案锁只能作用于当前SHOT，solution_lock_scope必须为shot",
            )
        position = vector(shot.get("camera_position_world"))
        forward = vector(shot.get("camera_forward_world"))
        height = number(shot.get("camera_height"))
        if position is None:
            add_error("invalid_observation_signature", f"SHOT {shot_id or index}.camera_position_world必须是3维数字数组")
        if forward is None or direction_similarity(forward, forward) < 0:
            add_error("invalid_observation_signature", f"SHOT {shot_id or index}.camera_forward_world必须是非零3维向量")
        if height is None:
            add_error("invalid_observation_signature", f"SHOT {shot_id or index}.camera_height必须是数字")
        inherited = shot.get("camera_station_inherited_from_previous")
        if not isinstance(inherited, bool):
            add_error(
                "invalid_camera_inheritance_contract",
                f"SHOT {shot_id or index}.camera_station_inherited_from_previous必须为布尔值",
            )
        parsed.append(shot)

    pair_reports: list[dict[str, Any]] = []
    for index in range(1, len(parsed)):
        previous, current = parsed[index - 1], parsed[index]
        near, equal_dimensions = near_equivalent(previous, current)
        same_station = text(previous.get("camera_station_id")) == text(current.get("camera_station_id"))
        inherited = current.get("camera_station_inherited_from_previous") is True
        if inherited and same_station and not motivated(current):
            add_error(
                "camera_inherited_without_directorial_reason",
                f"SHOT {text(current.get('shot_id'))}在CUT后继承上一摄影点，但没有repetition_intent与repetition_payoff",
            )
        if not inherited and same_station:
            add_warning(
                "unmarked_camera_station_reuse",
                f"SHOT {text(current.get('shot_id'))}复用上一摄影点，但未标记camera_station_inherited_from_previous=true",
            )
        pair_reports.append({
            "from_shot_id": text(previous.get("shot_id")),
            "to_shot_id": text(current.get("shot_id")),
            "same_station": same_station,
            "near_equivalent": near,
            "equal_dimensions": equal_dimensions,
        })

    windows: list[dict[str, Any]] = []
    for start in range(0, max(0, len(parsed) - window_size + 1)):
        window = parsed[start : start + window_size]
        station_ids = [text(item.get("camera_station_id")) for item in window]
        all_same_station = len(set(station_ids)) == 1
        pair_near = []
        pair_dimensions = []
        for index in range(1, len(window)):
            near, equal_dimensions = near_equivalent(window[index - 1], window[index])
            pair_near.append(near)
            pair_dimensions.append(equal_dimensions)
        all_near = bool(pair_near) and all(pair_near)
        repetition_motivated = all(motivated(item) for item in window[1:])
        repetitive = all_same_station or all_near
        shot_ids = [text(item.get("shot_id")) for item in window]
        if repetitive and not repetition_motivated:
            add_error(
                "repetitive_observation_sequence",
                f"连续SHOT {shot_ids}重复同一摄影点或近似观察签名；不能只更换说话主体而保持同一视角",
            )
        windows.append({
            "shot_ids": shot_ids,
            "all_same_station": all_same_station,
            "all_near_equivalent": all_near,
            "repetition_motivated": repetition_motivated,
            "pair_equal_dimensions": pair_dimensions,
        })

    # Scene-level sanity: a dialogue or relationship sequence with at least four
    # shots should not collapse to one station unless repetition is explicitly
    # designed. Different medium-shot stations remain valid.
    if len(parsed) >= 4:
        unique_stations = {text(item.get("camera_station_id")) for item in parsed}
        if len(unique_stations) == 1 and not all(motivated(item) for item in parsed[1:]):
            add_error(
                "single_station_scene_coverage",
                "四个以上SHOT全部使用同一camera_station_id，且没有明确重复意图与回报",
            )

    return {
        "ok": not errors,
        "scene_id": scene_id,
        "shot_count": len(parsed),
        "unique_camera_station_count": len({text(item.get('camera_station_id')) for item in parsed}),
        "pair_reports": pair_reports,
        "rolling_windows": windows,
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

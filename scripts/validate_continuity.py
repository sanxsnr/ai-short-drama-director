#!/usr/bin/env python3
"""Validate explicit state inheritance between SHOTs or SEGs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MISSING = object()
ALLOWED_TRANSITION_TYPES = {
    "continuous",
    "time",
    "space",
    "dream",
    "memory",
    "montage",
}


def load_payload(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def get_path(data: object, dotted_path: str) -> Any:
    current = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    shots = payload.get("shots")
    segments = payload.get("segments")
    if shots is not None and segments is not None:
        errors.append("shots 与 segments 只能提供一个")
        units = shots if isinstance(shots, list) else []
        unit_name = "SHOT"
    elif shots is not None:
        units = shots
        unit_name = "SHOT"
    else:
        units = segments
        unit_name = "SEG"

    if not isinstance(units, list) or len(units) < 2:
        errors.append("shots 或 segments 至少包含两个单元")
        units = []

    by_id: dict[str, dict] = {}
    for index, unit in enumerate(units, start=1):
        if not isinstance(unit, dict):
            errors.append(f"{unit_name}[{index}] 必须是对象")
            continue
        unit_id = str(unit.get("id", "")).strip()
        if not unit_id:
            errors.append(f"{unit_name}[{index}] 缺少 id")
            continue
        if unit_id in by_id:
            errors.append(f"{unit_name} id 重复：{unit_id}")
            continue
        by_id[unit_id] = unit
        if not isinstance(unit.get("start_state"), dict):
            errors.append(f"{unit_id}缺少 start_state")
        if not isinstance(unit.get("end_state"), dict):
            errors.append(f"{unit_id}缺少 end_state")

    transitions = payload.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        errors.append("transitions 必须是非空数组")
        transitions = []

    checked_paths = 0
    for index, transition in enumerate(transitions, start=1):
        if not isinstance(transition, dict):
            errors.append(f"transitions[{index}] 必须是对象")
            continue
        from_id = str(transition.get("from", "")).strip()
        to_id = str(transition.get("to", "")).strip()
        if from_id not in by_id or to_id not in by_id:
            errors.append(f"转场{index}引用未知单元：{from_id} → {to_id}")
            continue

        transition_type = str(transition.get("type", "continuous")).strip().lower()
        if transition_type not in ALLOWED_TRANSITION_TYPES:
            errors.append(
                f"转场{from_id} → {to_id}的 type 无效：{transition_type}"
            )
            transition_type = "continuous"

        inherit = transition.get("inherit", [])
        if not isinstance(inherit, list) or not all(isinstance(x, str) for x in inherit):
            errors.append(f"转场{from_id} → {to_id}的 inherit 必须是字符串数组")
            inherit = []

        allowed_changes = transition.get("allowed_changes", [])
        if not isinstance(allowed_changes, list) or not all(
            isinstance(x, str) for x in allowed_changes
        ):
            errors.append(
                f"转场{from_id} → {to_id}的 allowed_changes 必须是字符串数组"
            )
            allowed_changes = []

        non_applicable = transition.get("non_applicable", [])
        if not isinstance(non_applicable, list) or not all(
            isinstance(x, str) for x in non_applicable
        ):
            errors.append(
                f"转场{from_id} → {to_id}的 non_applicable 必须是字符串数组"
            )
            non_applicable = []

        if transition_type == "continuous" and not inherit:
            errors.append(
                f"连续转场{from_id} → {to_id}必须声明 inherit 路径"
            )
        elif transition_type != "continuous" and not inherit:
            warnings.append(
                f"{transition_type}转场{from_id} → {to_id}没有继承任何剧情或资产状态；"
                "确认人物服装、伤势、道具和剧情结果是否真的全部不适用"
            )

        end_state = by_id[from_id].get("end_state", {})
        start_state = by_id[to_id].get("start_state", {})
        for path in inherit:
            checked_paths += 1
            if path in non_applicable:
                errors.append(
                    f"转场{from_id} → {to_id}的路径{path}同时出现在 inherit 和 non_applicable"
                )
                continue
            before = get_path(end_state, path)
            after = get_path(start_state, path)
            if before is MISSING:
                errors.append(f"{from_id}.end_state 缺少继承路径：{path}")
                continue
            if after is MISSING:
                errors.append(f"{to_id}.start_state 缺少继承路径：{path}")
                continue
            if before != after and path not in allowed_changes:
                errors.append(
                    f"连续性冲突 {from_id} → {to_id}｜{path}："
                    f"{before!r} != {after!r}"
                )

        for path in allowed_changes:
            if path not in inherit:
                warnings.append(
                    f"转场{from_id} → {to_id}允许变化路径未列入 inherit：{path}"
                )

        if transition.get("copies_previous_frame") is True:
            warnings.append(
                f"转场{from_id} → {to_id}标记复制上一画面；"
                "状态继承不等于复制尾帧，除非明确使用I2V／FLF2V工作流"
            )
        if transition.get("keeps_same_camera") is True:
            warnings.append(
                f"转场{from_id} → {to_id}标记保持同一机位；"
                "确认这是同一SHOT而不是错误地跨CUT保持机位"
            )

    return {
        "ok": not errors,
        "unit_type": unit_name,
        "unit_count": len(by_id),
        "transition_count": len(transitions),
        "checked_path_count": checked_paths,
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

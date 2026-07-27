#!/usr/bin/env python3
"""Validate explicit inheritance paths between short-drama segments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MISSING = object()


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

    segments = payload.get("segments")
    if not isinstance(segments, list) or len(segments) < 2:
        errors.append("segments 至少包含两个段落")
        segments = []

    by_id: dict[str, dict] = {}
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            errors.append(f"segments[{index}] 必须是对象")
            continue
        segment_id = str(segment.get("id", "")).strip()
        if not segment_id:
            errors.append(f"segments[{index}] 缺少 id")
            continue
        if segment_id in by_id:
            errors.append(f"段落 id 重复：{segment_id}")
            continue
        by_id[segment_id] = segment
        if not isinstance(segment.get("start_state"), dict):
            errors.append(f"段落{segment_id}缺少 start_state")
        if not isinstance(segment.get("end_state"), dict):
            errors.append(f"段落{segment_id}缺少 end_state")

    transitions = payload.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        errors.append("transitions 必须是非空数组，并显式声明需要继承的路径")
        transitions = []

    checked_paths = 0
    for index, transition in enumerate(transitions, start=1):
        if not isinstance(transition, dict):
            errors.append(f"transitions[{index}] 必须是对象")
            continue
        from_id = str(transition.get("from", "")).strip()
        to_id = str(transition.get("to", "")).strip()
        if from_id not in by_id or to_id not in by_id:
            errors.append(f"转场{index}引用未知段落：{from_id} → {to_id}")
            continue
        inherit = transition.get("inherit")
        if not isinstance(inherit, list) or not all(isinstance(x, str) for x in inherit):
            errors.append(f"转场{from_id} → {to_id}的 inherit 必须是字符串数组")
            continue
        if not inherit:
            warnings.append(f"转场{from_id} → {to_id}没有声明任何继承路径")
        allowed_changes = transition.get("allowed_changes", [])
        if not isinstance(allowed_changes, list):
            errors.append(f"转场{from_id} → {to_id}的 allowed_changes 必须是数组")
            allowed_changes = []

        end_state = by_id[from_id].get("end_state", {})
        start_state = by_id[to_id].get("start_state", {})
        for path in inherit:
            checked_paths += 1
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

    return {
        "ok": not errors,
        "segment_count": len(by_id),
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

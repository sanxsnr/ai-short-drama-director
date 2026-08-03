#!/usr/bin/env python3
"""Validate SEG timing, SHOT timing, dialogue capacity and optional CUT metadata."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

PUNCTUATION_RE = re.compile(r"[\s，。！？、；：,.!?;:“”‘’（）()\[\]【】…—\-]")
ALLOWED_CUT_TYPES = {
    "CUT",
    "MATCH-ON-ACTION",
    "REACTION",
    "EYELINE",
    "INSERT",
    "SPACE",
    "TIME",
    "POV",
    "END",
}


def visible_char_count(text: str) -> int:
    return len(PUNCTUATION_RE.sub("", text or ""))


def load_payload(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def almost_equal(a: float, b: float, tolerance: float = 0.05) -> bool:
    return math.isclose(a, b, abs_tol=tolerance)


def normalize_cut_type(value: object) -> str:
    text = str(value or "").strip().upper().replace("_", "-")
    aliases = {
        "普通CUT": "CUT",
        "MATCH CUT": "MATCH-ON-ACTION",
        "MATCH-ON-ACTION CUT": "MATCH-ON-ACTION",
        "REACTION CUT": "REACTION",
        "EYELINE CUT": "EYELINE",
        "INSERT CUT": "INSERT",
        "SPACE CUT": "SPACE",
        "TIME CUT": "TIME",
        "POV CUT": "POV",
    }
    return aliases.get(text, text)


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    mode = str(payload.get("segment_mode", "10s"))
    try:
        target = float(payload.get("target_duration", 0))
    except (TypeError, ValueError):
        target = 0.0
        errors.append("target_duration 必须是数字")

    content_type = str(payload.get("content_type", "mixed"))
    shots = payload.get("shots", [])
    enforce_cut_fields = payload.get("enforce_cut_fields", True) is not False

    absolute_limit = 13.0 if mode == "10s" else 18.0 if mode == "15s" else None
    if absolute_limit is None:
        errors.append("segment_mode 必须是 10s 或 15s")
    elif target > absolute_limit + 0.05:
        errors.append(f"总时长 {target:g}s 超过 {mode} 模式绝对上限 {absolute_limit:g}s")

    if target <= 0:
        errors.append("target_duration 必须大于0")
    if content_type not in {"dialogue", "action", "montage", "mixed"}:
        errors.append("content_type 必须是 dialogue、action、montage 或 mixed")
    if not isinstance(shots, list) or not shots:
        errors.append("shots 必须是非空数组")
        return {"ok": False, "errors": errors, "warnings": warnings}

    expected_start = 0.0
    total_dialogue_chars = 0

    for index, shot in enumerate(shots, start=1):
        if not isinstance(shot, dict):
            errors.append(f"shots[{index}] 必须是对象")
            continue
        try:
            start = float(shot["start"])
            end = float(shot["end"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"SHOT {index} 缺少有效 start/end")
            continue

        if not almost_equal(start, expected_start):
            errors.append(
                f"SHOT {index}从 {start:g}s 开始，但上一SHOT结束于 {expected_start:g}s"
            )
        if end <= start:
            errors.append(f"SHOT {index}结束时间必须晚于开始时间")
            expected_start = max(expected_start, end)
            continue

        duration = end - start
        dialogue_chars = visible_char_count(str(shot.get("dialogue", "")))
        total_dialogue_chars += dialogue_chars
        capacity = duration * 4.5
        if dialogue_chars > capacity + 1:
            warnings.append(
                f"SHOT {index}约{dialogue_chars}字对白 / {duration:g}s，"
                f"超过正常语速容量约{capacity:.1f}字"
            )

        is_last = index == len(shots)
        cut_type = normalize_cut_type(shot.get("cut_type"))
        cut_point = str(shot.get("cut_point", "")).strip()

        if enforce_cut_fields:
            if is_last:
                if cut_type and cut_type != "END":
                    warnings.append(
                        f"终镜SHOT {index}的 cut_type 为 {cut_type}；本场／本集结束时建议使用 END"
                    )
            else:
                if not cut_type:
                    errors.append(f"SHOT {index}缺少 cut_type")
                elif cut_type not in ALLOWED_CUT_TYPES - {"END"}:
                    errors.append(f"SHOT {index}的 cut_type 无效：{cut_type}")
                if not cut_point:
                    errors.append(f"SHOT {index}缺少具体 cut_point")

        expected_start = end

    if target > 0 and not almost_equal(expected_start, target):
        errors.append(
            f"最后一SHOT结束于 {expected_start:g}s，与目标总时长 {target:g}s 不一致"
        )

    total_capacity = target * 4.5
    if total_dialogue_chars > total_capacity + 1:
        warnings.append(
            f"全SEG约{total_dialogue_chars}字对白 / {target:g}s，"
            f"超过正常语速容量约{total_capacity:.1f}字"
        )
    elif target > 0:
        dialogue_rate = total_dialogue_chars / target
        if dialogue_rate > 4.0:
            warnings.append(
                f"全SEG对白密度约{dialogue_rate:.1f}字/秒，接近物理上限；"
                "优先压缩重复信息或拆分SEG，不删除合法CUT"
            )
        elif dialogue_rate > 3.5:
            warnings.append(
                f"全SEG对白密度约{dialogue_rate:.1f}字/秒，需检查停顿和动作空间"
            )

    # SHOT数量本身不构成错误或警告。镜头密度必须根据CUT动机、机位几何和时长判断。
    return {
        "ok": not errors,
        "mode": mode,
        "target_duration": target,
        "content_type": content_type,
        "shot_count": len(shots),
        "dialogue_char_count": total_dialogue_chars,
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

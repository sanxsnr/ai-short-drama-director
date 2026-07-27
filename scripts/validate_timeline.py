#!/usr/bin/env python3
"""Validate AI short-drama segment and shot timing from JSON."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path


PUNCTUATION_RE = re.compile(r"[\s，。！？、；：,.!?;:“”‘’（）()\[\]【】…—\-]")


def visible_char_count(text: str) -> int:
    return len(PUNCTUATION_RE.sub("", text or ""))


def load_payload(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def almost_equal(a: float, b: float, tolerance: float = 0.05) -> bool:
    return math.isclose(a, b, abs_tol=tolerance)


def validate(payload: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    mode = str(payload.get("segment_mode", "10s"))
    target = float(payload.get("target_duration", 0))
    pacing = str(payload.get("pacing", "stable"))
    content_type = str(payload.get("content_type", "mixed"))
    shots = payload.get("shots", [])

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
        return {"ok": not errors, "errors": errors, "warnings": warnings}

    expected_start = 0.0
    total_dialogue_chars = 0
    pacing_soft_limit = {"fast": 3.2, "stable": 6.5, "one-take": target}.get(pacing)
    if pacing_soft_limit is None:
        errors.append("pacing 必须是 fast、stable 或 one-take")
        pacing_soft_limit = target

    for index, shot in enumerate(shots, start=1):
        try:
            start = float(shot["start"])
            end = float(shot["end"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"镜头{index}缺少有效 start/end")
            continue

        if not almost_equal(start, expected_start):
            errors.append(
                f"镜头{index}从 {start:g}s 开始，但上一镜结束于 {expected_start:g}s"
            )
        if end <= start:
            errors.append(f"镜头{index}结束时间必须晚于开始时间")
            expected_start = max(expected_start, end)
            continue

        duration = end - start
        dialogue_chars = visible_char_count(str(shot.get("dialogue", "")))
        total_dialogue_chars += dialogue_chars
        capacity = duration * 4.5

        if dialogue_chars > capacity + 1:
            warnings.append(
                f"镜头{index}约{dialogue_chars}字对白 / {duration:g}s，"
                f"超过正常语速容量约{capacity:.1f}字"
            )
        if duration > pacing_soft_limit + 0.05 and pacing != "one-take":
            warnings.append(
                f"镜头{index}时长 {duration:g}s 超过 {pacing} 模式软建议 "
                f"{pacing_soft_limit:g}s；有持续表演、位移或运镜即可保留"
            )
        expected_start = end

    if target > 0 and not almost_equal(expected_start, target):
        errors.append(
            f"最后一镜结束于 {expected_start:g}s，与目标总时长 {target:g}s 不一致"
        )

    total_capacity = target * 4.5
    if total_dialogue_chars > total_capacity + 1:
        warnings.append(
            f"全段约{total_dialogue_chars}字对白 / {target:g}s，"
            f"超过正常语速容量约{total_capacity:.1f}字"
        )
    elif target > 0:
        dialogue_rate = total_dialogue_chars / target
        if dialogue_rate > 4.0:
            warnings.append(
                f"全段对白密度约{dialogue_rate:.1f}字/秒，接近物理上限；"
                "优先压缩重复信息或增加可用时长"
            )
        elif dialogue_rate > 3.5:
            warnings.append(
                f"全段对白密度约{dialogue_rate:.1f}字/秒，属于较密区间；"
                "需检查情绪停顿和动作空间"
            )

    shot_ranges = {
        "dialogue": {"10s": (1, 3), "15s": (2, 4)},
        "action": {"10s": (2, 5), "15s": (3, 6)},
        "montage": {"10s": (3, 6), "15s": (4, 8)},
        "mixed": {"10s": (1, 5), "15s": (2, 7)},
    }
    if mode in {"10s", "15s"} and content_type in shot_ranges:
        low, high = shot_ranges[content_type][mode]
        if len(shots) > high:
            warnings.append(
                f"{content_type} 类型的 {mode} 段共有{len(shots)}镜，"
                f"高于常用范围{low}—{high}镜；检查是否误把故事板格数当成切镜数"
            )

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

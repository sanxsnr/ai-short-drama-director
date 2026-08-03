#!/usr/bin/env python3
"""Validate unique rule-source ownership and cross-file rule contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "skill": ROOT / "SKILL.md",
    "script": ROOT / "references/01-script-slicing.md",
    "spatial": ROOT / "references/04-blocking-continuity.md",
    "cut": ROOT / "references/13-cut-shot-geometry.md",
}

FORBIDDEN = {
    "skill": [
        "## CUT优先分镜规则",
        "### 禁止相邻镜头",
        "## 空间确认Gate",
        "## 信息可见性检查",
    ],
    "script": [
        "## 30度规则",
        "## 两变量规则",
        "## 禁止切到相邻镜头",
        "## 跨SHOT状态继承",
        "## 信息可见性",
    ],
    "spatial": [
        "## 有效CUT触发条件",
        "## CUT类型",
        "## 30度规则",
        "## 景别跨级规则",
        "## 两变量规则",
    ],
    "cut": [
        "## 场景方向与坐标",
        "## 人物空间状态",
        "## 道具空间状态",
        "## 跨SHOT状态继承",
        "## 信息可见性\n",
    ],
}

REQUIRED_REFERENCES = {
    "skill": [
        "references/01-script-slicing.md",
        "references/04-blocking-continuity.md",
        "references/13-cut-shot-geometry.md",
    ],
    "script": ["04-blocking-continuity.md", "13-cut-shot-geometry.md"],
    "spatial": ["13-cut-shot-geometry.md"],
    "cut": ["04-blocking-continuity.md"],
}

AMBIGUOUS_SEG_SHOT_PHRASES = (
    "一个10秒SHOT内部不得再出现第二个CUT",
    "一个10秒SHOT内部不得出现第二次CUT",
    "同一SHOT内不得再出现",
    "SHOT内部不得再出现第二个CUT",
)

SINGLE_SHOT_SEG_CONTRACT = (
    "每个10秒SEG必须且只能包含1个SHOT",
    "SEG内部不包含CUT",
)

SPATIAL_GEOMETRY_CONTRACT = (
    "人物—剧情对象—运动—摄影机几何求解",
    "推导可见面",
    "唯一方案锁",
    "无动机看镜头",
)

SKILL_GEOMETRY_CONTRACT = (
    "只有`04`输出“几何结论：通过”后",
    "唯一方案锁",
    "validate_spatial_geometry.py",
)


def appears_before(text: str, first: str, second: str) -> bool:
    first_index = text.find(first)
    second_index = text.find(second)
    return first_index >= 0 and second_index >= 0 and first_index < second_index


def validate(root: Path = ROOT) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    texts: dict[str, str] = {}
    for name, relative in FILES.items():
        path = root / relative.relative_to(ROOT)
        if not path.exists():
            errors.append(f"缺少核心规则文件：{path.relative_to(root)}")
            continue
        texts[name] = path.read_text(encoding="utf-8")

    for name, phrases in FORBIDDEN.items():
        text = texts.get(name, "")
        for phrase in phrases:
            if phrase in text:
                errors.append(
                    f"{FILES[name].relative_to(ROOT)} 重复定义了不属于本文件的规则标题："
                    f"{phrase.strip()}"
                )

    for name, refs in REQUIRED_REFERENCES.items():
        text = texts.get(name, "")
        for ref in refs:
            if ref not in text:
                errors.append(f"{FILES[name].relative_to(ROOT)} 缺少唯一真源引用：{ref}")

    skill_text = texts.get("skill", "")
    if "其他文件只能引用这些真源，不得另写一套同类规则" not in skill_text:
        warnings.append("SKILL.md 未明确禁止其他文件重新定义同类规则。")

    skill_order_valid = (
        appears_before(skill_text, "2. `04`锁定", "3. `13`决定")
        or appears_before(skill_text, "2. `04`锁定", "`13`才能决定")
    )
    if not skill_order_valid:
        errors.append(
            "SKILL.md 的分镜职责顺序必须明确为：04先锁定空间事实，13再决定SHOT/CUT。"
        )

    for phrase in SKILL_GEOMETRY_CONTRACT:
        if phrase not in skill_text:
            errors.append(f"SKILL.md 缺少空间几何入口合同：{phrase}")

    spatial_text = texts.get("spatial", "")
    for phrase in SPATIAL_GEOMETRY_CONTRACT:
        if phrase not in spatial_text:
            errors.append(
                f"references/04-blocking-continuity.md 缺少空间几何合同：{phrase}"
            )

    cut_text = texts.get("cut", "")
    if not appears_before(
        cut_text,
        "`04`已确认的空间状态与上一SHOT结束状态",
        "本文件的CUT和机位几何规则",
    ):
        errors.append("13-cut-shot-geometry.md 必须把04空间事实置于CUT决策规则之前。")

    for name in ("skill", "script", "cut"):
        text = texts.get(name, "")
        for phrase in AMBIGUOUS_SEG_SHOT_PHRASES:
            if phrase in text:
                errors.append(
                    f"{FILES[name].relative_to(ROOT)} 混淆了SEG／SHOT／CUT：{phrase}"
                )

    for name in ("script", "cut"):
        text = texts.get(name, "")
        for phrase in SINGLE_SHOT_SEG_CONTRACT:
            if phrase not in text:
                errors.append(
                    f"{FILES[name].relative_to(ROOT)} 缺少单SHOT SEG明确合同：{phrase}"
                )

    geometry_validator = root / "scripts/validate_spatial_geometry.py"
    if not geometry_validator.exists():
        errors.append("缺少空间几何验证器：scripts/validate_spatial_geometry.py")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

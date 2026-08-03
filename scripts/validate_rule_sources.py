#!/usr/bin/env python3
"""Validate unique rule-source ownership across the core Skill markdown files."""

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
                errors.append(f"{FILES[name].relative_to(ROOT)} 重复定义了不属于本文件的规则标题：{phrase.strip()}")

    for name, refs in REQUIRED_REFERENCES.items():
        text = texts.get(name, "")
        for ref in refs:
            if ref not in text:
                errors.append(f"{FILES[name].relative_to(ROOT)} 缺少唯一真源引用：{ref}")

    skill_text = texts.get("skill", "")
    if "其他文件只能引用这些真源，不得另写一套同类规则" not in skill_text:
        warnings.append("SKILL.md 未明确禁止其他文件重新定义同类规则。")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

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
    "video": ROOT / "references/05-video-prompting.md",
    "qc": ROOT / "references/06-qc-repair-post.md",
    "storyboard": ROOT / "references/07-storyboard-image-prompts.md",
    "beginner": ROOT / "references/11-beginner-guided-mode.md",
    "output": ROOT / "references/12-output-format-and-choice-footer.md",
    "cut": ROOT / "references/13-cut-shot-geometry.md",
    "agent": ROOT / "agents/openai.yaml",
    "production_template": ROOT / "assets/production-document-template.md",
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
        "## 相邻SHOT视觉差异闸门",
        "## 视觉差异充分性",
        "## 禁止切到相邻镜头",
        "## 跨SHOT状态继承",
        "## 信息可见性",
    ],
    "spatial": [
        "## 有效CUT触发条件",
        "## CUT类型",
        "## 30度规则",
        "## 相邻SHOT视觉差异闸门",
        "## 视觉差异充分性",
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
    "180度轴线、人物朝向与`04`空间事实始终高于30度经验规则",
    "叙事变化不能代替视觉差异",
    "validate_spatial_geometry.py",
)

CUT_DIFFERENCE_CONTRACT = (
    "## 相邻SHOT视觉差异闸门",
    "30度规则只在以下条件同时成立时重点适用",
    "同轴大景别路径",
    "角度路径与同轴大景别路径是替代关系",
    "组合路径必须至少包含两项**视觉变化**",
    "叙事变化不计入视觉变化数量",
    "180度轴线与`04`空间事实是硬约束",
    "## 视觉差异充分性",
    "无意的近似机位跳切",
)

STALE_GLOBAL_PHRASES = (
    "相邻SHOT是否满足30度、景别差异、两变量",
    "每次CUT至少改变两个有效视觉变量",
    "禁止相邻机位和相邻景别",
    "无相邻机位、相邻景别或近似构图",
    "前后是相邻机位、相邻景别或近似构图",
    "相邻机位和相邻景别造成无效跳切",
    "满足30度和两变量规则",
    "标准两变量路径要求每次CUT至少改变两个有效维度",
    "第二项可以是另一视觉维度，也可以是",
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

    for phrase in CUT_DIFFERENCE_CONTRACT:
        if phrase not in cut_text:
            errors.append(f"references/13-cut-shot-geometry.md 缺少视觉差异合同：{phrase}")

    if "不是相邻SHOT之间的30度剪辑规则" not in spatial_text:
        errors.append("04必须明确区分单机位可见面角度与相邻SHOT的30度剪辑规则。")

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml"}:
            continue
        if any(part in {".git", "tests", "__pycache__"} for part in path.parts):
            continue
        text_value = path.read_text(encoding="utf-8")
        for phrase in STALE_GLOBAL_PHRASES:
            if phrase in text_value:
                errors.append(
                    f"{path.relative_to(root)} 保留了过时或累计式视觉差异规则：{phrase}"
                )

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

    readme = root / "README.md"
    if readme.exists():
        readme_text = readme.read_text(encoding="utf-8")
        for phrase in ("validate_cut_geometry.py", "13-cut-shot-geometry.md"):
            if phrase not in readme_text:
                errors.append(f"README.md 缺少当前仓库结构或验证器说明：{phrase}")

    readme_en = root / "README_EN.md"
    if readme_en.exists() and "validate_cut_geometry.py" not in readme_en.read_text(encoding="utf-8"):
        errors.append("README_EN.md 缺少CUT视觉差异验证器说明：validate_cut_geometry.py")

    geometry_validator = root / "scripts/validate_spatial_geometry.py"
    if not geometry_validator.exists():
        errors.append("缺少空间几何验证器：scripts/validate_spatial_geometry.py")

    cut_geometry_validator = root / "scripts/validate_cut_geometry.py"
    if not cut_geometry_validator.exists():
        errors.append("缺少CUT视觉差异验证器：scripts/validate_cut_geometry.py")
    if "validate_cut_geometry.py" not in skill_text:
        errors.append("SKILL.md 缺少CUT视觉差异验证器入口：validate_cut_geometry.py")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

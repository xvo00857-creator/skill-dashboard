#!/usr/bin/env python3
"""校验 Skill 目录的 SKILL.md 是否合规。"""
import sys
import os
import re

PLACEHOLDER_PATTERNS = [
    r"a brief description",
    r"describe when this skill",
    r"instructions for the agent",
    r"first step",
]

def validate(skill_dir):
    errors = []
    skill_md = os.path.join(skill_dir, "SKILL.md")
    dir_name = os.path.basename(os.path.normpath(skill_dir))

    if not os.path.isfile(skill_md):
        errors.append(f"[{dir_name}] 缺少 SKILL.md")
        return errors

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        errors.append(f"[{dir_name}] 缺少 YAML frontmatter（--- 包裹）")
        return errors

    frontmatter = m.group(1)
    name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)

    if not name_match or not name_match.group(1).strip():
        errors.append(f"[{dir_name}] frontmatter 缺少 name")
    elif name_match.group(1).strip() != dir_name:
        errors.append(f"[{dir_name}] name='{name_match.group(1).strip()}' 与目录名 '{dir_name}' 不一致")

    if not desc_match or not desc_match.group(1).strip():
        errors.append(f"[{dir_name}] frontmatter 缺少 description")
    else:
        desc = desc_match.group(1).strip().lower()
        for pat in PLACEHOLDER_PATTERNS:
            if re.search(pat, desc):
                errors.append(f"[{dir_name}] description 仍为占位文本")
                break

    return errors

def main():
    if len(sys.argv) < 2:
        print("用法: validate_skill.py <skill-dir> [<skill-dir> ...]")
        sys.exit(2)

    all_errors = []
    for d in sys.argv[1:]:
        all_errors.extend(validate(d))

    if all_errors:
        for e in all_errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    else:
        print(f"PASS: {len(sys.argv)-1} 个 Skill 全部合规")
        sys.exit(0)

if __name__ == "__main__":
    main()

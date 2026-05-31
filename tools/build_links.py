#!/usr/bin/env python3
"""Build bidirectional wikilinks across the math vault."""

import os
import re
from pathlib import Path

VAULT = Path(os.path.expanduser("~/Desktop/kaoyan-math-ai"))

# Directories to scan for .md files
SCAN_DIRS = ["数一", "0. 杂项"]

# Directories to skip
SKIP_DIRS = {".git", ".obsidian", "模版文件夹", "tools", "tests", "fig",
             "张宇", "Excalidraw", "assets"}

# Min concept name length to avoid false positives
MIN_NAME_LEN = 3

# Build concept -> filepath mapping
def build_concept_map():
    """Map concept names to their relative paths."""
    concept_map = {}  # concept_name -> relative_path (without .md)
    for scan_dir in SCAN_DIRS:
        base = VAULT / scan_dir
        if not base.exists():
            continue
        for md in base.rglob("*.md"):
            rel = md.relative_to(VAULT)
            name = md.stem
            # Skip mind maps, index files, very short names
            if "思维导图" in name:
                continue
            if re.match(r"^\d+-\d+\s", name):  # chapter index like "1-1 xxx"
                continue
            if len(name) < MIN_NAME_LEN:
                continue
            # Store with and without .md extension
            path_str = str(rel.with_suffix(""))
            if name not in concept_map:
                concept_map[name] = path_str
            else:
                # Keep the one with shorter path (more specific)
                if len(path_str) < len(concept_map[name]):
                    concept_map[name] = path_str
    return concept_map

def is_already_linked(text, pos, concept):
    """Check if concept at pos is already inside a wikilink."""
    # Look backwards for [[ before any ]]
    before = text[:pos]
    last_open = before.rfind("[[")
    last_close = before.rfind("]]")
    return last_open > last_close

def add_links_to_file(filepath, concept_map):
    """Add wikilinks to a file where concepts are mentioned."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except:
        return 0

    # Don't modify files that are mostly frontmatter or very short
    lines = text.split("\n")
    # Skip frontmatter
    content_start = 0
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                content_start = i + 1
                break

    # Build content portion
    content = "\n".join(lines[content_start:])
    if len(content.strip()) < 50:
        return 0

    # Sort concepts by length (longest first) to avoid partial matches
    sorted_concepts = sorted(concept_map.keys(), key=len, reverse=True)

    modifications = 0
    new_text = text

    for concept in sorted_concepts:
        # Skip if concept name is the same as this file's name
        if concept == filepath.stem:
            continue

        # Find all occurrences in the content portion
        # Use word boundary-ish matching for Chinese
        pattern = re.escape(concept)

        # Search and replace, but only first occurrence per paragraph
        parts = new_text.split("\n\n")
        for i, part in enumerate(parts):
            # Only process content parts (skip frontmatter)
            if i == 0 and "---" in part:
                continue

            # Check if concept appears and is not already linked
            match = re.search(pattern, part)
            if match and not is_already_linked(part, match.start(), concept):
                # Replace first occurrence with wikilink
                linked = f"[[{concept_map[concept]}|{concept}]]"
                parts[i] = part.replace(concept, linked, 1)
                modifications += 1

        new_text = "\n\n".join(parts)

    if modifications > 0:
        filepath.write_text(new_text, encoding="utf-8")

    return modifications

def create_chapter_indexes():
    """Create index files for each chapter."""
    chapters = {
        "数一/1 高数/0 汇总": "高数方法与思维汇总",
        "数一/1 高数/1 函数 极限与连续": "函数、极限与连续",
        "数一/1 高数/2 一元函数微分学及其应用": "一元函数微分学",
        "数一/1 高数/3 微分中值定理": "微分中值定理",
        "数一/1 高数/4 一元函数积分学及其应用": "一元函数积分学",
        "数一/1 高数/5 空间解析几何与场论": "空间解析几何与场论",
        "数一/1 高数/6 多元函数微分学及其应用": "多元函数微分学",
        "数一/1 高数/7 二重积分及其应用": "二重积分",
        "数一/1 高数/8 微分方程": "微分方程",
        "数一/1 高数/9 无穷级数": "无穷级数",
        "数一/1 高数/10 线面积分": "线面积分",
        "数一/2 线代/1 行列式": "行列式",
        "数一/2 线代/2 矩阵": "矩阵",
        "数一/2 线代/3 向量组": "向量组",
        "数一/2 线代/4 线性方程组": "线性方程组",
        "数一/2 线代/5 特征值与特征向量": "特征值与特征向量",
        "数一/2 线代/6 二次型": "二次型",
        "数一/3 概率论/1 随机事件与概率": "随机事件与概率",
        "数一/3 概率论/2 一维随机变量及其分布": "一维随机变量",
        "数一/3 概率论/3 二维随机变量及其分布": "二维随机变量",
        "数一/3 概率论/4 随机变量的数字特征": "数字特征",
        "数一/3 概率论/5 大数定律和中心极限定理": "大数定律与中心极限定理",
        "数一/3 概率论/6 数理统计的基本概念": "数理统计基本概念",
        "数一/3 概率论/7 参数估计": "参数估计",
        "数一/3 概率论/8 假设检验": "假设检验",
    }

    created = 0
    for dir_path, title in chapters.items():
        full_dir = VAULT / dir_path
        if not full_dir.exists():
            continue

        index_path = full_dir / f"0-目录-{title}.md"
        if index_path.exists():
            continue

        # Collect all .md files in this directory (not subdirs)
        files = sorted(full_dir.glob("*.md"))
        files = [f for f in files if f != index_path and "思维导图" not in f.stem and "目录" not in f.stem]

        if not files:
            continue

        content = f"""---
属性: 目录
tags: [索引]
---

# {title}

"""
        # Group by subdirectory
        root_files = []
        subdirs = {}
        for f in files:
            rel = f.relative_to(full_dir)
            if len(rel.parts) == 1:
                root_files.append(f)
            else:
                subdir = rel.parts[0]
                if subdir not in subdirs:
                    subdirs[subdir] = []
                subdirs[subdir].append(f)

        # Add mind map if exists
        mindmaps = [f for f in full_dir.glob("*思维导图*.md")]
        if mindmaps:
            content += "## 思维导图\n\n"
            for mm in mindmaps:
                content += f"- [[{mm.stem}]]\n"
            content += "\n"

        # Root level files
        if root_files:
            content += "## 知识点\n\n"
            for f in root_files:
                content += f"- [[{f.stem}]]\n"
            content += "\n"

        # Subdirectory files
        for subdir, subfiles in sorted(subdirs.items()):
            content += f"## {subdir}\n\n"
            for f in subfiles:
                content += f"- [[{f.stem}]]\n"
            content += "\n"

        # Navigation
        content += "---\n\n"
        # Find parent and sibling chapters
        parts = dir_path.split("/")
        if "1 高数" in dir_path:
            content += "[[高等数学总目录]] | "
        elif "2 线代" in dir_path:
            content += "[[线性代数总目录]] | "
        elif "3 概率论" in dir_path:
            content += "[[概率论总目录]] | "
        content += "[[欢迎]]\n"

        index_path.write_text(content, encoding="utf-8")
        created += 1

    return created


def create_subject_indexes():
    """Create top-level subject index files."""
    subjects = {
        "数一/1 高数": ("高等数学总目录", "高等数学", [
            "1 函数 极限与连续", "2 一元函数微分学及其应用", "3 微分中值定理",
            "4 一元函数积分学及其应用", "5 空间解析几何与场论", "6 多元函数微分学及其应用",
            "7 二重积分及其应用", "8 微分方程", "9 无穷级数", "10 线面积分"
        ]),
        "数一/2 线代": ("线性代数总目录", "线性代数", [
            "1 行列式", "2 矩阵", "3 向量组",
            "4 线性方程组", "5 特征值与特征向量", "6 二次型"
        ]),
        "数一/3 概率论": ("概率论总目录", "概率论与数理统计", [
            "1 随机事件与概率", "2 一维随机变量及其分布", "3 二维随机变量及其分布",
            "4 随机变量的数字特征", "5 大数定律和中心极限定理",
            "6 数理统计的基本概念", "7 参数估计", "8 假设检验"
        ]),
    }

    created = 0
    for dir_path, (filename, title, chapters) in subjects.items():
        full_dir = VAULT / dir_path
        index_path = full_dir / f"{filename}.md"
        if index_path.exists():
            continue

        content = f"""---
属性: 目录
tags: [索引]
---

# {title}

"""
        for ch in chapters:
            ch_dir = full_dir / ch
            if ch_dir.exists():
                content += f"## [[{ch}]]\n\n"
                # List files in this chapter
                files = sorted(ch_dir.glob("*.md"))
                for f in files[:5]:
                    if "思维导图" not in f.stem and "目录" not in f.stem:
                        content += f"- [[{f.stem}]]\n"
                remaining = len([f for f in files if "思维导图" not in f.stem and "目录" not in f.stem]) - 5
                if remaining > 0:
                    content += f"- ...还有 {remaining} 个知识点\n"
                content += "\n"

        content += "---\n\n[[欢迎]] | [[高等数学总目录]] | [[线性代数总目录]] | [[概率论总目录]]\n"
        index_path.write_text(content, encoding="utf-8")
        created += 1

    return created


if __name__ == "__main__":
    print("Building concept map...")
    concept_map = build_concept_map()
    print(f"Found {len(concept_map)} concepts")

    print("\nCreating chapter index files...")
    idx_count = create_chapter_indexes()
    print(f"Created {idx_count} chapter indexes")

    print("\nCreating subject index files...")
    subj_count = create_subject_indexes()
    print(f"Created {subj_count} subject indexes")

    print("\nAdding bidirectional links...")
    total_links = 0
    for scan_dir in SCAN_DIRS:
        base = VAULT / scan_dir
        if not base.exists():
            continue
        for md in base.rglob("*.md"):
            if "思维导图" in md.stem or "目录" in md.stem:
                continue
            links = add_links_to_file(md, concept_map)
            if links > 0:
                total_links += links
                print(f"  {md.relative_to(VAULT)}: +{links} links")

    print(f"\nTotal: {idx_count} chapter indexes, {subj_count} subject indexes, {total_links} links added")

#!/usr/bin/env python3
"""make_samples.py —— 由 16x16 像素数据生成 10 个像素风示例 SVG 到 icons/"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "icons"
OUT.mkdir(exist_ok=True)

def rows_to_svg(name, rarity, pal, rows):
    """像素行 -> SVG rect（同行相邻同色格子合并，缩小体积）"""
    rects, palette_note = [], ", ".join(f"{k}={v}" for k, v in pal.items())
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            ch = row[x]
            if ch == ".": x += 1; continue
            x2 = x
            while x2 < len(row) and row[x2] == ch: x2 += 1
            rects.append(f'  <rect x="{x}" y="{y}" width="{x2-x}" height="1" fill="{pal[ch]}"/>')
            x = x2
    body = "\n".join(rects)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
            f'width="16" height="16" shape-rendering="crispEdges" '
            f'data-name="{name}" data-rarity="{rarity}">\n'
            f'  <!-- palette: {palette_note} -->\n{body}\n</svg>\n')

# ICONS = { "potion_healing": dict(name=..., rarity=..., pal=..., rows=[...16行...]), ... }
# （把上一轮回复中的 10 组像素数据按此结构填入即可）
for slug, spec in ICONS.items():
    (OUT / f"{slug}.svg").write_text(rows_to_svg(**spec), encoding="utf-8")
    print(f"icons/{slug}.svg  ({spec['name']}, {spec['rarity']})")

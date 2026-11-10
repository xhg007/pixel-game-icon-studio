#!/usr/bin/env python3
"""
svg2png.py —— 批量将 icons/*.svg 转换为多种尺寸 PNG，并生成 manifest.json 供 preview.html 使用

依赖:  pip install cairosvg
用法:
  python scripts/svg2png.py                        # 默认 icons/ -> png/{32,64,128}/
  python scripts/svg2png.py --sizes 64 256         # 自定义尺寸
  python scripts/svg2png.py --src icons --out png --bg "#1a140c"
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import cairosvg
except ImportError:
    sys.exit("缺少依赖，请先执行:  pip install cairosvg")


def parse_meta(svg_path: Path) -> dict:
    """从 SVG 根元素的 data-* 属性中提取名称与稀有度（单一数据源在 SVG 文件里）"""
    head = svg_path.read_text(encoding="utf-8")[:800]
    name = re.search(r'data-name="([^"]*)"', head)
    rarity = re.search(r'data-rarity="([^"]*)"', head)
    return {
        "name": name.group(1) if name else svg_path.stem,
        "rarity": rarity.group(1) if rarity else "common",
    }


def main():
    ap = argparse.ArgumentParser(description="SVG 图标批量转 PNG")
    ap.add_argument("--src", default="icons", help="SVG 源目录 (默认 icons)")
    ap.add_argument("--out", default="png", help="PNG 输出目录 (默认 png)")
    ap.add_argument("--sizes", type=int, nargs="+", default=[32, 64, 128],
                    help="输出尺寸列表，单位 px (默认 32 64 128)")
    ap.add_argument("--bg", default=None,
                    help='可选背景色(如 "#1a140c")，不填则保持透明')
    args = ap.parse_args()

    src = Path(args.src)
    out_root = Path(args.out)
    svgs = sorted(src.glob("*.svg"))
    if not svgs:
        sys.exit(f"错误: {src}/ 下没有找到任何 .svg 文件")

    manifest = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "src_dir": str(src), "out_dir": str(out_root), "icons": []}

    print(f"{'文件':<28}{'尺寸':<16}结果")
    print("-" * 60)
    for svg in svgs:
        meta = parse_meta(svg)
        pngs = {}
        for size in args.sizes:
            out_dir = out_root / str(size)
            out_dir.mkdir(parents=True, exist_ok=True)
            png_path = out_dir / f"{svg.stem}.png"
            try:
                cairosvg.svg2png(url=str(svg), write_to=str(png_path),
                                 output_width=size, output_height=size,
                                 background_color=args.bg)
                pngs[str(size)] = str(png_path).replace("\\", "/")
                print(f"{svg.name:<28}{size:>4}px{'':<10}OK")
            except Exception as e:
                print(f"{svg.name:<28}{size:>4}px{'':<10}FAIL: {e}")
        manifest["icons"].append({
            "id": svg.stem, "name": meta["name"], "rarity": meta["rarity"],
            "svg": str(svg).replace("\\", "/"), "png": pngs,
        })

    manifest_path = src / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(manifest["icons"])
    print("-" * 60)
    print(f"完成: {n} 个图标 x {len(args.sizes)} 种尺寸 -> {out_root}/  manifest -> {manifest_path}")
    print("现在可以直接用浏览器打开 preview.html 查看图库。")


if __name__ == "__main__":
    main()

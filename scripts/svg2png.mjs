#!/usr/bin/env node
/**
 * svg2png.mjs —— 批量将 icons/*.svg 转换为多种尺寸 PNG，并生成 manifest.json
 * 依赖:  npm install sharp
 * 用法:
 *   node scripts/svg2png.mjs                     # icons/ -> png/{32,64,128}/
 *   node scripts/svg2png.mjs --sizes 64 256
 *   node scripts/svg2png.mjs --bg "#1a140c"
 */
import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const args = process.argv.slice(2);
function argOf(name, def){
  const i = args.indexOf(name);
  return i === -1 ? def : args[i + 1];
}
const hasFlag = (name) => args.includes(name);

const SRC = argOf("--src", "icons");
const OUT = argOf("--out", "png");
const BG = hasFlag("--bg") ? argOf("--bg", undefined) : undefined;
const SIZES = hasFlag("--sizes")
  ? args[args.indexOf("--sizes") + 1].split(/[,\s]+/).map(Number)
  : [32, 64, 128];

const files = (await fs.readdir(SRC)).filter(f => f.endsWith(".svg")).sort();
if (!files.length) { console.error(`错误: ${SRC}/ 下没有 .svg 文件`); process.exit(1); }

const manifest = { generated_at: new Date().toISOString(), src_dir: SRC, out_dir: OUT, icons: [] };

for (const file of files){
  const svgPath = path.join(SRC, file);
  const buf = await fs.readFile(svgPath);
  const head = buf.toString("utf8", 0, 800);
  const meta = {
    name: head.match(/data-name="([^"]*)"/)?.[1] ?? path.basename(file, ".svg"),
    rarity: head.match(/data-rarity="([^"]*)"/)?.[1] ?? "common",
  };
  const pngs = {};
  for (const size of SIZES){
    const outDir = path.join(OUT, String(size));
    await fs.mkdir(outDir, { recursive: true });
    const outPath = path.join(outDir, path.basename(file, ".svg") + ".png");
    /* SVG 画布为 16px，按 density 渲染后用最近邻缩放，保证像素锐利 */
    try {
      let img = sharp(buf, { density: 72 * (size / 16) })
        .resize(size, size, { kernel: "nearest" });
      if (BG) img = img.flatten({ background: BG });
      await img.png().toFile(outPath);
      pngs[String(size)] = outPath.replaceAll("\\", "/");
      console.log(`${file.padEnd(28)}${String(size).padStart(4)}px      OK`);
    } catch (e){
      console.error(`${file.padEnd(28)}${String(size).padStart(4)}px      FAIL: ${e.message}`);
    }
  }
  manifest.icons.push({
    id: path.basename(file, ".svg"), ...meta,
    svg: svgPath.replaceAll("\\", "/"), png: pngs,
  });
}

await fs.writeFile(path.join(SRC, "manifest.json"),
  JSON.stringify(manifest, null, 2), "utf8");
console.log(`完成: ${manifest.icons.length} 个图标 x ${SIZES.length} 种尺寸 -> ${OUT}/`);
console.log("manifest -> " + path.join(SRC, "manifest.json"));

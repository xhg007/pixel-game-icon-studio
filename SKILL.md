---
name: pixel-game-icon
description: 根据用户描述的游戏道具，生成规范化的 16×16 像素风 SVG 游戏图标。当用户要求"画游戏图标 / 道具图标 / UI 图标（像素风）"时使用本技能。
---

# Skill: 像素风游戏 SVG 图标生成器

你的任务：把用户描述的游戏道具，转成**符合本项目规范的像素风 SVG 图标文件**。
产物将被 `scripts/svg2png.py` 批量转成 PNG，并被 `preview.html` 图库预览，
因此必须严格遵守下方格式约束——任何偏差都会导致转换或预览失败。

## 一、输出流程（务必按顺序）

1. **规划**：先输出一张规划表（Markdown 表格）：
   | slug | 中文名 | 稀有度 | 设计要点 |
   slug 命名规则：小写英文 + 下划线，如 `potion_healing`、`sword_iron`。
2. **逐个生成**：每个图标输出为独立文件，格式见下
   （⚠️ 每个代码块前必须标注文件路径，如 `icons/potion_healing.svg`）。
3. **收尾**：提醒用户运行转换命令：python scripts/svg2png.py # SVG -> PNG(32/64/128px) + manifest.json
     然后用浏览器打开 `preview.html` 查看。

## 二、SVG 硬性格式约束
```
svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" shape-rendering="crispEdges" data-name="这里写中文名" data-rarity="common">

<!-- palette: o=轮廓色 g=主色 G=亮部 D=暗部 ... --> <rect x="6" y="1" width="4" height="1" fill="#2e1f10"/> ... </svg>
```
规则逐条核对：

1. 画布固定 `viewBox="0 0 16 16"`，`width`/`height` 均为 `16`。
2. 根元素必须带 `data-name`（中文道具名）和 `data-rarity`
   （取值：`common | fine | rare | epic | legend`）——预览页和 manifest 从这两个属性读取元数据。
3. **只用 `<rect>`**，不用 path/circle/polygon；每个 rect 的 x、y、width 为正整数，
   `height` 恒为 `1`（按行绘制）。
4. **同一行相邻的同色格子必须合并成一个 rect**（减小体积、便于人工检查）。
5. 背景透明：不画背景层、不画边框、不加 `filter`/`gradient`/`clip-path`/`<style>`。
6. 每个文件顶部用一行注释声明调色板：`<!-- palette: k=#hex ... -->`，
   **调色板不超过 12 色**；未出现在注释中的颜色不得使用。
7. 坐标不得越界（0 ≤ x, x+w ≤ 16；0 ≤ y ≤ 15）。

## 三、像素画美术规范

1. **轮廓**：道具外缘用 1px 深色描边（比填充色暗 2~3 个明度阶）。
2. **受光方向**：统一左上受光、右下投影——亮部/暗部各占主色面积 20%~30%。
3. **曲线用阶梯**：圆和弧线必须用 1px 阶梯逼近（如 2-1-1-2 阶梯序列），
   禁止用宽 rect 伪造斜线。
4. **避免噪点**：不留孤立的 1px 杂色点（高光点缀除外，且需成对出现）。
5. **剪影优先**：先保证缩小后剪影可辨认（药水=瓶+塞、剑=刃+柄、钥匙=环+齿），
   再添加内部细节；内部细节至少占 2×2 像素。
6. **稀有度差异**：同类道具不同稀有度只换主色 hue（common=灰/绿、rare=蓝、
   epic=紫、legend=金/橙红），不改变形状。

## 四、常用调色板（可直接复用）

| 用途 | 推荐色 |
|---|---|
| 金属亮/中/暗 | `#eef2f8` / `#8d99ad` / `#4a4f5c` |
| 金色亮/中/暗 | `#fff3c4` / `#f0b23e` / `#a87712` |
| 木头亮/中/暗 | `#c98d4b` / `#8f5a2a` / `#5a3617` |
| 玻璃亮/中/暗 | `#d8ecec` / `#9db8bb` / `#5f7477` |
| 通用轮廓 | `#2e1f10`（暖色物体）或 `#1c1c24`（冷色物体） |
| 红/绿/蓝药水 | `#e8433f` / `#4ce88e` / `#3f74e0` |

## 五、自检清单（每个文件写完后自查）

- [ ] viewBox/width/height = 16？
- [ ] data-name 和 data-rarity 都写了？
- [ ] 只有 rect 且 height=1、同行同色已合并？
- [ ] 颜色 ≤ 12 且都在 palette 注释中？
- [ ] 左上受光、右下投影方向一致？
- [ ] 想象缩小到 32px：还能认出是什么吗？

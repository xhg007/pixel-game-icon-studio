### 使用流程
#### 1) 冷启动：生成 10 个示例图标
python tools/make_samples.py

#### 2) SVG → PNG + manifest（二选一，沙盒里已验证 cairosvg 路线 ✓）
uv add cairosvg && uv run scripts/svg2png.py

#### 3) 本地服务 + 打开预览
uv run python -m http.server
#### 浏览器访问 preview.html

### 几个设计要点：
元数据单一来源：data-name/data-rarity 写在 SVG 根元素上，转换脚本正则提取写入 manifest.json，预览页按它渲染稀有度色——改稀有度只需改 SVG 一处。
像素锐利保证：cairosvg 直接按 output_width 渲染矢量（rect 无反锯齿问题）；sharp 版用 density: 72 × size/16 + kernel: "nearest" 双保险。
预览页降级策略：找不到 manifest 时自动探测示例文件名，双击打开也能看图（但完整功能建议走本地服务）。
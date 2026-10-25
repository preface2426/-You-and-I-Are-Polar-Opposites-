# POPURI ·《正相反的你与我》便利店场景

无人物的动画风格场景，包含便利店、停车场、道路、卡车、连续围墙、住宅和路边围栏。旧版本已按原文件保存时间恢复为顺序 Git 提交，见 [归档说明](archive/README.md)。

## 直接看效果并自由移动

**推荐：双击 `打开实时场景.cmd`。** 启动本机 Blender 的 EEVEE 实时场景，无需另装引擎。右侧 `POPURI` 面板可以切换昼夜与店外、店内、通道、设备视角。点击 **自由漫游（WASD）** 进入步行视角（会先切换为透视视图），WASD 移动、鼠标转头、滚轮调速；左键确认，Esc 退出。也可从“视图 → 导航 → 步行导航”进入。

电动玻璃门会感应当前视点：接近到 3 米内且视点高度低于 3.2 米，左右两扇分别向外滑动 1.47 米；离开后延时 1.6 秒关闭。可取消“靠近自动开门”后用开合滑块检查。用户手动移动后的复印机位置已保留，目前与左门轨道、竖框有相交，检查报告已记录。

**轻量网页：双击 `Popuri_Gallery.html`。** 保持 `web/` 与 HTML 同目录，可完全离线打开。拖动旋转、滚轮缩放、右键平移；勾选“自由移动”后点击画面，WASD / Q E 移动升降，Shift 加速。电动门支持自动、保持打开、保持关闭。网页材质采用简化的卡通着色；Blender 实时版与最终静态图使用同一套 EEVEE 动画材质。

若通过 HTTP 查看，网页直接加载 `web/Popuri_Store.glb`；本地双击则使用压缩后的 `web/glb-data.js`。无需服务器或联网。网页静止时停止绘制，切到后台后暂停；默认限制像素比为 1，清晰模式最高 1.5。场景只保留 3 种材质，按空间合并网格，保留独立门扇。

## 与参考图对齐的内容

- 卡车在店前道路左侧，车头沿道路方向；道路与店面平行，停车场在两者之间。
- 后方和左侧住宅位于连续围墙之外，右侧围栏沿停车场延伸到路边。
- 顾客面对收银台时，白灰色 POS 在左，红色立式热食柜和棕框弧面展示柜在右；咖啡设备放在后工作台。
- POS 与咖啡机保持靠左。按最新参考图，后方改为五层深色分格小商品架及两块广告牌，降低后工作台，使商品在收银屏幕后方可见；80 个小商品保留紧密分区。
- 两侧长货架向收银区靠近 2.80 米，并向两侧各让开 0.20 米；前端采用开放陈列和浅蓝招牌，补上近收银区的竖装商品。中央净通道超过 1.40 米，收银台前横向通道超过 1.30 米。
- 用户于 22:46 保存的手动修改完整保存在 [用户基线](archive/user-edits-20261025-224643/README.md)。购物篮、复印机、L 形台、门垫、招牌等修改与删除均已保留；重建时先载入该基线，再更新货架。
- 两排货架围出朝向收银台的通道，提供对应参考图的检查视角。
- 当前工程与导出模型均无人物。原始归档保留旧文件原貌，可能含原有店员。
- 墙角、地基、天花板和屋面采用实质搭接；降低屋面补上原先顶部间隙，门口保留真实开口。

参考图没有提供完整尺寸或不可见部分，布局按可见位置关系重建；不会是逐像素一致的动画原作场景。

## 文件

| 文件 | 用途 |
|---|---|
| `Popuri_Store.blend` | 可编辑完整场景，含独立门扇和开合演示时间轴 |
| `打开实时场景.cmd` / `Open_Popuri.ps1` | 启动 EEVEE 实时场景与视点感应门 |
| `Popuri_Gallery.html` / `web/` | 离线轻量自由视角查看器 |
| `renders/` | 最终室内、收银设备、夜景、店面、货架通道 PNG |
| `popuri_build.py` / `popuri_style.py` / `popuri_checkout.py` | 保留手动修改基线后重建货架布局与动画材质 |
| `popuri_live.py` | Blender 实时昼夜、视角与自动门 |
| `popuri_render.py` / `render_final.ps1` | 渲染指定视角 / 重渲染全部成图 |
| `export_popuri_web.py` / `gzip_glb.py` | 精简 GLB 与离线压缩数据 |
| `archive/` | 9 个旧快照及修改前完整 Popuri 备份 |
| `design/` | 原有平面和多视图设计 SVG |
| `recordings/` | 原屏幕录像，仅保留在本机，不上传公开仓库 |

## 重建与验证

使用当前本机 Blender 5.4 Alpha（可执行文件在 `D:\Blender`）。在以下命令中将 `blender` 替换为实际可执行文件路径：

```powershell
blender -b --python-exit-code 1 --python popuri_build.py
blender -b Popuri_Store.blend --python-exit-code 1 --python tests/verify_scene.py
blender -b Popuri_Store.blend --python-exit-code 1 --python tests/verify_user_edits.py
blender -b Popuri_Store.blend --python-exit-code 1 --python tests/verify_live.py
blender -b Popuri_Store.blend --python-exit-code 1 --python export_popuri_web.py
python gzip_glb.py
.\render_final.ps1
```

浏览器检查需要 Python Playwright 和 Chrome，仅用于测试，查看器没有这些运行依赖：

```powershell
python tests/test_viewer.py
```

几何检查覆盖主要壳体连接、双门行程、开门通道和复印机避让、卡车所处道路及收银设备顺序。实时脚本检查覆盖视点感应和昼夜切换。浏览器检查覆盖离线加载、两门开关、离开后关闭、自由移动、屋顶切换、控制台错误与静止停止绘制。测试结果见 `web/scene-checks.json`、`web/model-stats.json` 和 `web/performance.json`。

Blender 导航操作依据 [Blender 官方 Fly/Walk 文档](https://docs.blender.org/manual/en/4.0/editors/3dview/navigate/walk_fly.html)；动画材质使用 [Shader to RGB](https://docs.blender.org/manual/en/4.1/render/shader_nodes/converter/shader_to_rgb.html)，需 EEVEE 渲染。

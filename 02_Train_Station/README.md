# 动画电车与站台

来自用户引用聊天中的六张原作截图，保持 POPURI 便利店的 EEVEE 动画材质风格。无人物，保留可识别的空间布局，细节采用适量简化。

## 打开

**推荐双击 `打开电车站台.cmd`**，启动本机 Blender，右侧 `STATION` 面板可以选择站台尽头、横向、反向、列车外观、车厢内部、长椅、入口和总览。选好视角后点击 **自由漫游（WASD）**，鼠标转头、滚轮调速、Q / E 升降；左键确认、Esc 退出。侧栏可切换昼夜、隐藏车顶，以及手动或按视点距离开关站台侧车门。

也可直接打开 `Train_Station.blend` 编辑模型。只有使用启动器才会启用本地视点感应脚本；文件本身的几何、材质、相机和门扇驱动均已保存。

**离线网页：双击 `Station_Gallery.html`**，保持 `web/` 文件夹在旁边。拖动旋转、滚轮缩放、右键平移；勾选自由移动后点击画面，WASD / Q E 移动升降，Shift 加速。可以切换雨棚、车顶和站台侧车门。停下操作后停止绘制，后台标签页暂停。

网页采用简化卡通材质，完整着色以 Blender 和 `renders/` 中的原生渲染图为准。HTTP 查看时直接加载 GLB；本地双击时使用压缩嵌入数据。无外部 CDN 或运行时联网依赖。

## 场景与依据

- 中央 H 型钢柱、双坡钢雨棚、两侧黄色盲道、绿色边线、接触网与高架城市背景。
- 浅银车体和蓝色外侧腰带；车内绿色长椅、橙色地板、米色隔板、海绿色扶手、白色三角吊环、行李架与吊挂广告。
- 两节相连的车厢；站台侧双扇门向前后滑开，另一侧保持关闭。保留完整可看的内部通道。
- 街面宽楼梯和右侧扶梯，以及另一个站台向上楼梯与扶梯；雨棚为上行楼梯留出开口。
- 动画中不可辨认的站名和广告文字以色块表达。没有把该站认定为あざみ野，也没有把列车冒认成某个已确定车型。
- 站台尽头渲染图中的列车为远处驶来状态，其余大部分视角为停靠状态，是同一场景的两个时间点。

[参考核对与多轮修改记录](references/VERIFICATION.md) 区分了原作可见特征、已查官方材料和建模推定。相关漫画章节当前需要租阅，未读取付费分镜；具体车型、完整站厅和背面连接仍属推定。两节车、车长与轨距等是建模尺度假设。

## 最终图

| 图片 | 内容 |
|---|---|
| `renders/Platform_Day.png` | 站台尽头、钢柱雨棚和远处列车 |
| `renders/Platform_Across.png` | 站台横向、上行楼梯与扶梯 |
| `renders/Platform_Reverse.png` | 反向纵深与入口方向 |
| `renders/Train_Exterior.png` | 蓝带电车外观与站台 |
| `renders/Carriage_Aisle.png` | 无人车厢、绿色长椅与三角吊环 |
| `renders/Carriage_Bench.png` | 长椅、端板、大窗与车门 |
| `renders/Station_Entrance.png` | 街面入口、楼梯和右侧扶梯 |
| `renders/Station_Overview.png` | 轨道、站台、站房与周边概览 |

## 重建和检查

本机使用 `D:\Blender` 下的 Blender 5.4 Alpha；启动器会从 PATH 或该目录查找可执行文件。以下 `blender` 可换成实际路径：

```powershell
blender -b --python-exit-code 1 --python station_build.py
blender -b Train_Station.blend --python-exit-code 1 --python tests/verify_station.py
blender -b Train_Station.blend --python-exit-code 1 --python tests/verify_live.py
blender -b Train_Station.blend --python-exit-code 1 --python station_export.py
python gzip_glb.py
.\render_final.ps1
```

浏览器检查需要 Python Playwright 和 Chrome；这些仅用于测试，查看器无需安装：

```powershell
python tests/test_viewer.py
```

几何检查覆盖轮轨和受电弓接触、16 个活动门扇的行程与避让、36 个入口楼梯点、26 个站台上行楼梯点、17 个车内通道点和 142 个站台侧通路点。实时检查确认门扇实际移动。网页检查覆盖自由移动、门扇、屋顶、离线加载和静止停绘。结果保存在 `web/scene-checks.json` 与 `web/performance.json`。

尚未验证其他 Blender 版本及其他设备的帧率。

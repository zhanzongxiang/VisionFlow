# VisionFlow 项目审计与优化规划

审计日期：2026-09-29。对象是本地工作区，包含尚未提交的 YOLO 与 `game_daily.py` 相关代码，不等同于 GitHub 已发布版本。

## 先读结论

当前问题不是需要更换 Python 或重写桌面界面，而是新增功能已经超过单文件架构能够稳定承载的范围。

建议顺序：

1. 先修复停止/关闭、YOLO 判断校验、模型路径、错误分支与日常任务时限问题。
2. 再优化已经测到的热点：素材库刷新、多尺度模板匹配、截图后端选择。
3. 将运行器、设备、识别、存储逐步从界面代码中抽离，保留 PySide6 和现有流程图。
4. 在同一个执行核心上扩展“视觉日常”，不要长期维护两套相互独立的任务语义。

首次审计只新增审计工具、测量结果和规划文档，并补充 README 入口，没有修改业务运行代码。后续已实施第一批问题修复，详见 [04 修复与验证](04-fix-verification.md)；下方首次基线数据保持原样。

## 文档导航

| 文档 | 用途 |
| --- | --- |
| [01 项目现状与问题审计](01-current-state-and-findings.md) | 当前架构、分级问题、源码证据、复现与测试边界 |
| [02 性能优化与目标架构](02-performance-and-architecture.md) | 实测基线、优化取舍、模块边界、数据与线程设计 |
| [03 实施路线与验收](03-implementation-plan.md) | 任务拆分、依赖顺序、估算、验证、迁移及回滚 |
| [04 第一批修复与验证](04-fix-verification.md) | YOLO 判断、停止/关闭、模型路径和打包检查修复，含剩余限制 |
| [fixes-recheck.json](fixes-recheck.json) | 修复后的离线问题探针 |
| [fixes-source-smoke.txt](fixes-source-smoke.txt) | 修复后的优化模式源码冒烟 |
| [fixes-frozen-smoke.txt](fixes-frozen-smoke.txt) | 修复后的冻结包依赖与图像/OCR 冒烟 |
| [baseline.json](baseline.json) | 环境信息、源码指纹、第一轮问题探针与性能原始数据 |
| [probes.json](probes.json) | 补充停止后动作分发探针后的复现结果 |
| [source-smoke.txt](source-smoke.txt) | 源码环境 Qt / 中文图片 / RapidOCR 冒烟记录 |
| [审计脚本](../../tools/audit_project.py) | 可复跑的离线探针和合成性能测量 |

## 本轮验证

- 现有测试：61 项通过；这是测试数量，不是覆盖率。
- 依赖检查：`pip check` 通过。
- 源码冒烟：Qt 初始化、中文路径图片、缩放匹配和真实 RapidOCR 推理通过。
- YOLO：验证了解码/调用链和错误模型形状的合成输出；没有真实游戏模型精度或性能结果。
- 没有实测真实模拟器的最小化、输入接收、多显示器/DPI、长时间并发和干净 Windows 安装。

## 关键测量

| 场景 | 中位耗时 |
| --- | ---: |
| 100 张 PNG 素材时修改一次节点名称 | 195.583 ms |
| 上述改名触发图片解码 | 101 次 |
| 1920×1080 全图、九尺度模板匹配 | 733.754 ms |
| 320×200 ROI、九尺度匹配实验 | 22.534 ms |
| 500 个动作节点的画布重建 | 47.278 ms |

以上为本机合成负载、预热后各 7 次采样，不包含真实截图和游戏响应时间。ROI 实验不是已经实现的自动优化，也不能直接作为产品加速承诺。

## 复跑

在项目根目录使用现有虚拟环境：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -p "test_*.py" -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe tools/audit_project.py --output docs/audit-2026-09-29/recheck.json --samples 7
```

仅复现问题可加 `--probes-only`。探针中的 `observed: true` 表示旧问题被观察到，不表示修复通过；修复后要更新相应探针并加入正式回归测试。不要覆盖首次基线，比较时同时保留源码 SHA256 和环境信息。

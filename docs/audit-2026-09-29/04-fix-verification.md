# 第一批问题修复与验证

日期：2026-09-29。对应上一轮审计中的 F01、F02、F03、F12。

本次以修复测试反馈为范围，不进行界面重设计、架构拆分或全量性能优化。原始 `baseline.json`、`probes.json` 与 `source-smoke.txt` 保留不变。

## 已修改

| 问题 | 修改 | 验证方式 |
| --- | --- | --- |
| F01：YOLO 判断错误地要求模板图片 | 按 `image_exists` / `yolo_exists` 分别检查模板、ONNX 模型和目标类别；拒绝空条件、非法格式和未知类型；兼容旧图片条件与 AND / OR / NOT | 校验单测，以及经过实际 QThread 启动的模拟 YOLO 条件流程 |
| F02：停止后继续点击 | 步骤入口、图像识别返回、YOLO 截图/推理返回、新输入按下前检查停止；零时长等待也检查停止；仍允许释放已经按下的键鼠 | 识别中取消、输入前取消、按住后取消释放测试 |
| F02：ADB 阻塞导致长时间停止 | MuMu 查询、连接、截图、输入统一使用可取消的子进程执行器；轮询间隔最高 100 ms；取消/超时后回收当前客户端子进程，不关闭共享 ADB server | 实际启动休眠 Python 子进程，验证取消、超时、退出码和输出收集 |
| F02：模拟器截图先卡在 PrintWindow | 已找到 ADB 后端时直接使用 ADB；失败明确记录并交由识别层重试，不回退到可能陈旧的 Win32 图像 | 模拟 Win32 API，证明成功和失败路径都不调用 PrintWindow |
| F02：窗口关闭时销毁运行线程 | 第一次关闭确认后请求停止，使用 GUI 定时器等待线程退出；保留线程所有者，禁用编辑与再次启动；不重复询问保存/放弃；线程未停时不替换文档 | 真实阻塞 QThread 的关闭等待、放弃草稿恢复、新建/打开保护 |
| F02：任务已结束但状态仍运行中 | 在工作线程缓存完成结果，GUI 在线程清理时补处理可能因 QObject 销毁而失去发送者的完成通知 | 真实任务线程的完成状态回归 |
| F03：导出模型路径未同步 | 同步动作、条件中的 `image` 和 `model`；刷新选中节点属性，避免下一次编辑写回旧路径；自动草稿同步更新 | 中文外部模型路径跨目录导出、内存/画布/属性/草稿一致性、恢复、再次导出 |
| F12：优化打包跳过冒烟断言 | 将 `assert` 改为显式检查和异常，调用本身不会被 `optimize=1` 消除 | `python -O` 下分别注入两个匹配方法的错误返回，必须失败且报告 `FAIL` |

## 验证记录

- 全量 `unittest`：74 项通过，较原基线增加 13 项。这不是覆盖率统计。
- `pip check`：通过。
- 优化模式源码冒烟：Qt 窗口、中文图片路径、桌面/窗口图片匹配、多尺度匹配、比例适配、真实 RapidOCR 推理通过，见 `fixes-source-smoke.txt`。
- 更新离线探针后，F01、F03、F12 和 F02 的两个已知错误场景均为 `observed: false`，见 `fixes-recheck.json`。
- 优化冻结冒烟包：退出码 0，Qt、中文路径、图像匹配与真实 RapidOCR 均通过，见 `fixes-frozen-smoke.txt`。这是相同 spec 的专用测试入口，不是对正式 EXE 的真实业务操作验收。
- 全部测试使用临时 QSettings，不修改用户正常草稿；没有向真实游戏或模拟器发送鼠标、键盘或 ADB 输入。

## 可执行文件

修复版：`E:\me\py\dist-fixes-20260929\AutomationTool-small.exe`

- 文件大小：114,810,407 字节。
- SHA256：`F406498BFF6AF0BBAF3A0BABC2AD47749C09C394FA24BDEF0F53782BC883E0FD`。
- 采用现有 `AutomationTool-small.spec` 构建，未覆盖任何旧 EXE。
- 测试入口产物另存于 `dist-fixes-smoke-20260929`，不要把它当作正常应用启动。
- 本次没有发布 GitHub Release，也没有进行实际游戏窗口的点击验证。

## 仍然存在的边界

1. **不承诺任意目标程序都能立即停止。** 普通 Win32 的同步 PrintWindow、当前 ONNX 推理以及其他不可中断的原生调用仍需返回后才能结束线程。本次解决等待期间的线程生命周期安全；进程隔离和硬超时属于下一阶段。
2. **取消客户端不等于撤销已经送达设备的操作。** 已经提交给模拟器的长时间拖拽等操作能否立即终止，需要真实设备验证；后续步骤不会继续提交。
3. ADB 截图失败时现在明确重试/报错，不再使用 PrintWindow 回退画面。原因是后续输入仍走 ADB，混合陈旧帧和设备坐标可能误点击。普通非 ADB 窗口仍保留 PrintWindow。
4. 本轮没有解决 F04 条件错误与“未出现”的区分、F05 YOLO 输出协议兼容、F06 日常任务截止时间，也没有实现后续 ROI / 缓存 / 模块拆分。复查文件如实保留这些问题的 `observed: true`。
5. 真实游戏模型精度、最小化模拟器兼容性、多屏/DPI、长时间并发、干净 Windows 安装仍需集成验收。

## 本地复跑

```powershell
.\.venv\Scripts\python.exe -m unittest discover -p "test_*.py" -v
.\.venv\Scripts\python.exe -m pip check
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -O packaging_smoke.py docs/audit-2026-09-29/local-smoke.txt
.\.venv\Scripts\python.exe tools/audit_project.py --probes-only --output docs/audit-2026-09-29/local-recheck.json
```

探针的 `observed: false` 仅表示对应场景没有复现，不代表整个模块没有缺陷。不要覆盖首次基线。

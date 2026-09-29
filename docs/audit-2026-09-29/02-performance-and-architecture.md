# 02 性能优化与目标架构

本文件是设计建议，不表示已经实施。问题编号对应 [01 审计](01-current-state-and-findings.md)，交付顺序对应 [03 实施](03-implementation-plan.md)。

## 1. 测量方法与边界

- 平台：Windows build 22631，Intel Core i7-12700KF，12 核/20 逻辑处理器；Python 3.11.15。
- OpenCV 配置的线程数为 20，这不是实测同时占用 20 个核的结论。
- 图片为固定随机种子生成的 BGR 像素，模板 80×48，目标放置于已知位置。
- 每种操作预热 1 次，再采样 7 次；p95 使用 nearest-rank，因此这里恰好等于最大值。采样太少，不可作为生产 SLA。
- GUI 在 Qt offscreen 下运行，QSettings 指向临时 INI，窗口枚举返回空列表，使用临时生成的 PNG；不读取用户草稿，不截取真实桌面，不发送输入。
- GUI 数字是同步 Python/Qt 方法耗时，未测真实屏幕绘制帧率、交互到呈现延迟。
- 源码 SHA256、依赖版本和详细结果保存在 `baseline.json`。没有把 mock YOLO 的耗时伪称为真实推理速度。

## 2. 已测热点

| 场景 | median/ms | p95 小样本/ms | 解释 |
| --- | ---: | ---: | --- |
| 1280×720 九尺度匹配 | 348.036 | 365.671 | 当前默认搜索策略 |
| 1280×720 单尺度实验 | 40.815 | 41.942 | 不含缩放容错，不能直接替换默认行为 |
| 1280×720 截取 320×200 ROI，九尺度 | 21.285 | 22.217 | ROI 包含目标，未实现自动寻找 ROI |
| 1920×1080 九尺度匹配 | 733.754 | 744.609 | 全图匹配计算量明显 |
| 1920×1080 单尺度实验 | 79.924 | 80.954 | 保留原搜索范围，取消其他尺度 |
| 1920×1080 截取 320×200 ROI，九尺度 | 22.534 | 26.755 | 收益来自搜索面积减少 |
| 1920×1080 全图 `frame.std()` | 21.286 | 23.756 | 可优化，但优先级低于匹配和重复截图 |
| 隐藏素材库刷新，20 张 PNG | 40.369 | 42.264 | 原图 320×180 |
| 修改节点名称，20 张 PNG | 38.688 | 42.798 | 同步解码 21 次 |
| 隐藏素材库刷新，100 张 PNG | 196.285 | 206.305 | 图片未变化也重做 |
| 修改节点名称，100 张 PNG | 195.583 | 210.526 | 同步解码 101 次 |
| 自动保存，单等待节点/100 张无引用素材 | 3.882 | 5.075 | 仅小草稿，不代表大型宏草稿 |
| 100 动作节点画布重建 | 8.941 | 9.381 | 不包含最终绘制 |
| 500 动作节点画布重建 | 47.278 | 49.535 | 所有图元重新创建 |
| 500 动作节点全量更新边 | 3.804 | 4.266 | 鼠标移动时会重复发生 |
| 500 动作节点流程校验 | 0.608 | 1.132 | 当前不值得优先微优化 |

**结论：先消除无关工作，再优化算法和并发。** 本次测量不支持“换语言才能解决性能”的结论。流程校验虽有正确性问题，但纯耗时并不是首要瓶颈。

## 3. 性能实施建议

### O1：素材索引与缩略图增量化，优先级最高

关联 F07，现有入口 `app.py:6580`、`6625`、`8054`。

1. 区分 `node_properties_changed`、`asset_references_changed`、`asset_files_changed`；改名称不触发原图解码。
2. 素材页不可见时只标记索引/展示待更新；打开时按版本差异刷新，不重建全部 QListWidgetItem。
3. 缓存键为规范化路径、`mtime_ns`、文件大小和缩略图尺寸；内容替换时失效。重要模型使用内容哈希，不把路径视为版本。
4. 用有内存上限的 LRU 缓存缩略图和详情预览。初始预算可试 64 MiB，按真实素材负载调整。
5. IO 和缩放在后台处理 QImage；QPixmap、控件和列表模型更新留在 GUI 线程。批量通知/取消过期加载任务。
6. 文件监视仅提示增量变更，保留“刷新”恢复入口；不要递归监听整个盘。

验收：100 张图片时纯名称编辑解码次数为 0；同机热态同步处理 p95 < 50 ms。素材引用、删除保护、外部文件替换和中文路径回归不减少。

### O2：识别范围与尺度策略

关联 `app.py:1350`、`1372`、`4490`、`4557`。

- 先提供显式 ROI，限定窗口/安卓原始画面中的区域；ROI 外目标视为未命中，UI 预览必须能显示范围。
- 缓存每个模板的九个缩放版本和是否近乎纯色的统计，避免每个轮询重复 resize/meanStdDev。
- 模板文件缓存位于任务或识别服务中，按文件指纹失效。当前代码是在每次进入步骤读取模板，不是每次轮询都从磁盘重读，要避免误判收益来源。
- 可增加“上一命中区域/尺度 -> 局部 -> 全图”的分层策略，但必须明确它会改变搜索顺序。对多个相似按钮，提前返回可能改变原来全局最高分目标；默认策略保持兼容，优化策略显式启用并做误点测试。
- 灰度匹配只作为可选策略；颜色本身是区分信号时不能默认去掉颜色。
- 各次匹配之间检查取消与总 deadline；九尺度中也应设置可取消检查点。

目标：为真实素材建立固定黄金集，验证检测结果、误检率与点击中心；在收益相同的方案中优先保留语义。ROI 合成测试约 23 ms 是方向证据，不是全图自动识别能无条件达到的指标。

### O3：设备会话优先选择一个截图后端

关联 F02/F10，`app.py:3975`。

当前 MuMu 路径先 GDI/PrintWindow，再启动 ADB 截图并覆盖前一张画面。建议：

```text
已绑定 MuMu serial + ADB 健康
  -> 直接 ADB 原始截图
  -> Frame + transform

普通 Win32
  -> Win32 捕获适配器
  -> Frame + transform

后端异常
  -> 类型化错误 / 健康检查 / 明确的恢复策略
  -> 不在同一次输入中静默切到另一台设备或桌面
```

- 截图保持设备原生尺寸，预览才缩放；避免 ADB 画面先适配 Windows 客户区、YOLO 又 letterbox 的重复缩放。
- 兼容旧脚本时通过坐标适配层保留旧客户区尺寸，不直接改变已录制坐标语义。
- 一次判断周期使用同一个 Frame；多个目标共享截图。已有脚本“各自等待”语义单独保留，不能暗改。
- 初期仍可使用 `adb exec-out screencap -p`，先测端到端成本；持续视频流会增加协议、重连、解码和安装包复杂度，只有低频截图确实不够时再评估。
- Win32 DC/bitmap 复用要按目标尺寸失效并确保 GDI 释放；优化前后监测句柄数量。
- `frame.std()` 可尝试下采样健康指标，但不能把低纹理合法场景都判为坏图。帧 hash 不变也不等于冻结，静态菜单可能完全正常。

### O4：推理预算与模型生命周期

关联 `app.py:4627`、`4720`、`yolo_runtime.py:29`。

- 先明确 CPU 路径为基线，再评估 GPU。现在代码固定 CPUExecutionProvider，没有 GPU 实测数据。
- 任务数 × OCR session × YOLO session 的叠加可能造成线程过量和模型重复内存；这是静态风险，尚未测并发峰值。
- ONNX Runtime 显式设置线程选项，测 1/2/4 等候选值；用全局推理并发信号量控制同时运行数量。不能把某个固定线程数当作所有机器最佳值。[S4]
- 首先复用任务内 session；跨任务共享应由识别服务持有、明确串行队列或已验证的并发策略，不把全局可变实例随意交给所有 worker。
- 模型缓存以内容版本、设备/provider、输入配置为键，并有内存预算与引用计数；任务结束后可回收。
- 同一帧同一模型运行一次后再按类别筛选；截图变化后不可复用旧检测结果发送动作。
- `SessionOptions`、模型冷加载、预处理、推理和后处理分别计时；模型加载也需要预算，而不是在计时开始之前无限等待。

### O5：GUI、画布与日志

- 建立 node ID -> 相邻边索引，拖动时只更新相邻边；大图新增/删除图元增量完成。
- 暂不把 `FullViewportUpdate` 改回局部更新作为第一步，历史上出现过拖动残影与滚动崩溃；先减少无关布局，再通过实际截图/缩放/滚动测试决定绘制策略。
- 用固定间隔批量消费日志事件，例如每 100 ms 最多显示一批；错误和停止事件优先展示。限制排队长度，低级别重复日志可合并，但持久审计不能无声丢失。
- 日志改为结构化事件，错误数不再通过中文“超时”等子串计数；“开始识别，超时 10 秒”不应计为失败。
- 渲染纯文本，自动滚动仅在用户处于底部时启用；避免浏览历史时持续被拉回尾部。
- 保留最大 5,000 文档块作为显示保护，同时提供独立持久日志与轮转。

### O6：存储与发布

- 小草稿自动保存约 4 ms，目前无证据要求立刻换数据库。先修提交状态/备份，再测大型宏和多任务文档。
- worker 使用不可变任务快照；存储层接受快照，不从 GUI 场景对象反向提取业务数据。
- JSON 是导入/导出的契约，不必直接作为用户日常编辑入口；内部存储用应用数据目录和自动版本备份，用户只在导出时选择 JSON。
- 暂保留 one-file 便携包；并行评估 one-folder ZIP 的冷启动和增量更新成本。one-file 启动要先展开支持文件，因此体积与启动时间不能混为一个指标。[S6]
- 旧 EXE 为 114,801,344 字节，约 109.5 MiB；这是文件体积，不是运行内存。不要继续盲删 NumPy/ONNX/Qt 必要 DLL。
- 不因核心支持 YOLO 就打包 PyTorch 和训练依赖；训练工具环境与推理应用分开锁定。

## 4. 目标架构：模块化单体

保留 Python + PySide6 + QGraphicsView，初期不引入服务端、Electron、ReactFlow/G6 或消息中间件。

建议最终边界如下，不要求一次创建全部文件：

```text
app.py                         # 过渡入口，最终只做启动装配
game_daily.py                  # 保留兼容 CLI，转调同一 application API
visionflow/
  domain/
    models.py                  # Project/Task/Flow/Node/AssetRef/TargetSpec
    nodes.py                   # NodeSpec 与参数/条件协议
    validation.py              # 纯数据校验、流程编译
    errors.py                  # 错误码与不可取非的异常状态
  application/
    runner.py                  # 流程/轮次/节点调度
    daily_service.py           # 日常配置转换、确认策略
    cancellation.py            # 取消与 deadline
    device_leases.py            # 单设备互斥
    events.py                  # RunEvent/NodeEvent
  infrastructure/
    capture/win32.py
    capture/adb.py
    input/win32.py
    input/adb.py
    devices/mumu.py
    vision/template.py
    vision/ocr.py
    vision/yolo.py
    storage/projects.py
    storage/assets.py
    storage/migrations.py
    logging.py
  ui/
    main_window.py             # 只编排视图、控制器与信号
    controllers/
    pages/                    # tasks / flow / runs / assets / settings
    flow/                     # 场景、节点、边
    inspectors/               # 从 NodeSpec 创建当前节点有效字段
    qt_runner_bridge.py       # QObject/QThread 与纯执行器的桥接
  bootstrap.py                # 依赖注入与应用启动
tests/
  unit/
  integration/
  gui/
  fixtures/
  packaging/
tools/
  audit_project.py
```

依赖规则：

```text
UI / CLI -> application -> domain
infrastructure -> domain 中定义的协议
bootstrap -> 装配 application + infrastructure + UI/CLI
```

- domain/application 不导入 QWidget、MainWindow、pynput 或 ctypes。
- UI 不直接调用 ADB、ONNX Runtime、文件复制或 Win32 API。
- 图形场景只保存布局/选择；业务模型由文档控制器持有。`flow` 为唯一编辑源，`steps` 仅在兼容导出边界派生。
- CLI 不再依赖 ScriptWorker 私有方法，也不再重新实现识别与 deadline。
- 接口优先使用现有 Python 的 dataclass/Enum/Protocol；不为少量节点引入复杂插件框架。

## 5. 核心契约

| 契约 | 建议字段与规则 |
| --- | --- |
| TaskDocument | `task_id`、schema version、revision、target、flow、run_policy、asset refs；重命名不改变资源定位 |
| TargetSpec | backend family、明确实例选择策略、运行时 resolved device ID；HWND 不直接当跨重启持久 ID |
| Frame | BGR pixels、frame ID、采集时间、device ID、原生尺寸、坐标变换、健康状态 |
| MatchResult | FOUND/NOT_FOUND/ERROR/CANCELLED、bbox、score、class/text、frame ID、模型/模板版本 |
| ActionResult | DISPATCHED/CONFIRMED/FAILED/UNKNOWN；命令退出码为 0 仅说明发送，不等价于游戏接受 |
| RunContext | run/task/node IDs、round、deadline、cancel token、变量/上步结果、设备 lease、资源预算 |
| NodeSpec | type/version、参数 schema、默认值、编辑字段、校验器、执行处理器、素材引用提取 |
| AssetRef | 稳定 asset ID、kind、逻辑路径、指纹；图片与模型共用引用和导出机制 |

坐标必须有空间标签：desktop、window_client、device_native、ROI、model_input。检测结果始终带来源 Frame；点击只能映射到同一设备。旋转、窗口尺寸、DPI 或设备重连改变几何版本后，旧结果应重识别或明确拒绝。

不要为兼容而把每种坐标重新伪装成桌面坐标。旧版屏幕坐标在导入适配器中保留明确语义，并与新设备坐标节点区别开。

## 6. 执行与生命周期

```text
IDLE -> VALIDATING -> QUEUED -> RUNNING
RUNNING -> STOP_REQUESTED -> STOPPED
RUNNING -> SUCCEEDED / FAILED / TIMED_OUT
```

前置校验失败不启动设备动作。终态只提交一次，UI 通过 run ID 过滤旧事件，不依赖 `sender()` 的对象存活或中文消息决定状态。

- 一个设备一个动作拥有者；不同设备可以并发，但截图/推理资源由全局预算约束。
- 每一轮执行使用已验证快照；运行时编辑只影响下一次启动，UI 明确展示运行版本。
- deadline 用单调时钟，向截图、推理、输入和确认传递剩余预算；每次调用返回后复查。
- `stop` 禁止提交新动作；已提交但不可撤销的外部动作单独报告，不承诺立刻撤销。
- 关闭应用先请求停止并禁止启动新任务，等待 finished；不在 GUI 线程中无限阻塞，不删除尚在运行的 QThread。
- 对无法限时的本地调用按需隔离到子进程。仅为这类风险增加进程边界，不把每一个点击/每一个节点都启动成新进程。
- subprocess 超时处理必须终止并回收管道；超时和取消都需要 finally 清理。Python 官方示例也将 kill 与后续 communicate 配套处理。[S7]

## 7. 存储与迁移

1. 保留旧 QSettings 读取器，导入前备份原始 draft；修复前也不自动删除坏草稿。
2. 明确读写版本，未知未来版本拒绝覆盖；迁移函数是纯数据转换，可重复执行且有测试。
3. 新项目使用稳定 ID，内部存储位于用户可写数据目录；旧“任务名文件夹”先保留作为兼容解析根，不在首次启动大量搬移文件。
4. 资产改名与项目改名分离；只在显式整理/导出时复制或迁移，并保留事务计划。
5. 维护一条统一的相对路径解析规则，消除 runtime / 模板库 / exporter 三份逻辑优先级差异。
6. 先实现原子快照与备份；只有大量项目查询、历史检索成为实际需求时，再将索引和运行记录迁移至 SQLite。即使引入 SQLite，也不把图片/模型大文件默认塞入数据库。
7. 旧 JSON v4 到新版本的升级单独发版；在修复 P1 时不要顺带升级所有文档格式。

## 8. 产品与页面规划

保留已经认可的沉浸式布局，只增强工作流：

- 任务库：展示目标实例、实际后端、运行版本、运行/排队/停止状态；目标绑定可测试连接但不发送输入。
- 流程页：左侧画布、右侧有效属性，增加运行节点定位与校验结果；不要把模型训练参数塞进每一个节点。
- 素材页：图片/模型切换；右侧显示预览、类别列表、输入/输出协议、引用、验证结果和删除保护。
- 日志页：按 task/run/round/node 筛选，阶段耗时、错误码、失败截图、输入发送与确认分别显示。
- 设置页：全局资源预算、自动保存、日志保留；设备能力和任务配置仍留在任务详情。

YOLO 后续产品路线：截图采集 -> 数据版本/标注 -> 独立训练环境 -> 验证与 ONNX 导出 -> 模型注册 -> 只检测预演 -> 有界动作 -> 画面确认。没有真实标注数据和验证集，不应承诺通用游戏 AI。训练和自动化使用范围需要遵守目标软件规则，不能把模型识别能力等同于绕过反作弊或输入限制。

## 9. 暂不采纳的方案

| 方案 | 暂缓原因 | 重新评估条件 |
| --- | --- | --- |
| 全量重写为 C++/Rust | 已测热点大多来自重复工作和算法范围，重写会扩大回归面 | profile 证明纯 Python 核心循环占主导且已有清晰接口 |
| Web/G6/Electron 全替换 | 会新增桌面桥接、资源和打包复杂度，不能修复停止/坐标问题 | 现有画布无法满足协作、超大图或 Web 分发需求 |
| 全项目多进程化 | 取消、IPC、帧复制、模型内存都更复杂 | 特定不可信/阻塞 API 需要隔离，局部引入 |
| 默认 GPU | 尚无真模型基线；驱动与分发成本未评估 | CPU 无法达标且目标设备有稳定 GPU 环境 |
| 应用内集成完整训练框架 | 安装包与运行依赖明显扩张 | 独立训练助手或可选外部环境，而非默认运行包 |

## 参考资料

以下为官方资料入口，供实施时核对 API 与版本。外部资料用于约束设计，性能数值只来自本地测量。

- [S1] Microsoft Win32 `PrintWindow`：同步阻塞、由目标应用渲染。`https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-printwindow`
- [S2] Qt for Python `QThread`：worker 生命周期、quit/wait/finished；不能把 quit 当作中断任意阻塞函数。`https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html`
- [S3] Qt for Python `QSettings`：sync/status 和持久化错误处理。`https://doc.qt.io/qtforpython-6/PySide6/QtCore/QSettings.html`
- [S4] ONNX Runtime Thread management：intra-op、inter-op 和线程池调优。`https://onnxruntime.ai/docs/performance/tune-performance/threading.html`
- [S5] Ultralytics Export mode：ONNX、精度、动态维度和 NMS 导出设置。`https://docs.ultralytics.com/modes/export/`
- [S6] PyInstaller Operating Mode：one-file 与 one-folder 的执行过程。`https://pyinstaller.org/en/stable/operating-mode.html`
- [S7] Python 3.11 subprocess：超时、子进程终止与 communicate 清理。`https://docs.python.org/3.11/library/subprocess.html`

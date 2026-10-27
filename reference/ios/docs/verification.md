> 来源：[ios/docs/verification.md](https://github.com/mlboard-dev/ios/blob/d42eab1f37a90c5d171611f57556877f62e39fda/docs/verification.md) · `d42eab1`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 验证记录 · 2026-10-24

在 macOS / Xcode 27.0、iOS 27 simulator SDK 验证；全部缓存、派生数据、独立模拟器设备集和测试数据库留在工作区 `outputs/ios` 下。

| 验证 | 结果与证据 |
| --- | --- |
| Core / transport | 17 项通过；可选真实 HTTP 契约默认跳过，单独运行通过。覆盖并发 2、等待队列 16 上限/取消回收、2 MiB 流限制与 task 取消、Cookie/CSRF、403、超限 run 拒绝、Int64/缺值/额外 series 警告。日志 `core-tests.log`。 |
| 真实 HTTP 契约 | 新建隔离 SQLite 实例，63 runs、63 通知。Swift 客户端登录、组织项目、完整 runs/inbox 分页、路径搜索、三实验曲线、结构化直方图、单条通知读取/已读、PNG 下载与 logout 全部通过。`api-smoke-report.json`、`server-contract-tests.log`。 |
| Debug / Release | 两种配置的通用模拟器 ad-hoc 签名构建成功，`codesign --verify --strict --deep` 通过。日志 `build-debug-signed.log`、`build-release-signed.log`。Release 无 ATS HTTP 放行，APNs 环境为 production；Debug 为 sandbox。 |
| 原生 Keychain | 专用模拟器内首次启动写入/读取独立 probe，终止进程后第二次启动读取/删除全部通过。`keychain-write.json` 和 `keychain-read-delete.json`。Probe 不修改 session、不导航界面，Release 不包含它。 |
| 原生登录页 | 签名 app 成功启动，simctl 取得明暗截图 `screenshots/login-light.png`、`screenshots/login-dark.png`；已去除宣传副标题。unsigned 包曾出现 -34018，已改为默认模拟器 ad-hoc 签名并复验。 |

用户解锁并明确授权 XCUITest 后，在工作区专用设备集的 `MLBoard-QA` 完成真实 UI 输入、点击、滚动和截图复核，没有注入 App 会话或路由。追加结果如下（路径相对 `outputs/ios`）：

| 验收 | 结果与证据 |
| --- | --- |
| 完整操作链 | `test02ExperimentWorkflow` 通过，298.662 秒，`ui/workflow-05.xcresult`。真实登录、63 runs 分页、文件夹与搜索、3 run 比较、配置、曲线、直方图、鉴权 PNG、订阅保存及读回、63 通知分页、收件箱鉴权跳转、中英文切换、注销后重启。 |
| 冷启动恢复 | `test04SessionRestoresWithoutNotificationGate` 通过，55.538 秒，`ui/restore-01.xcresult`。真实登录后终止、重启，10 秒内进入可点击项目，再读取实验与注销。修复通知系统回调阻塞账号恢复。 |
| 中文 / 浅色 / 大字体 | `test03ChineseLargeTypeVisual` 通过，92.068 秒，`ui/visual-07.xcresult`。iOS `accessibility-large` 下实际滚动、选择三实验、点击比较、浏览单图和三实验曲线并注销；主代理复核截图。修复比较按钮被标签栏遮挡，以及状态标签断行、时间截断。 |
| 直方图 | `test05HistogramBars` 通过，61.761 秒，`ui/histogram-01.xcresult`。截图确认区间按零基线至计数绘制柱形，修复原先只画横线的问题。 |
| 最终构建 | Debug `ui/build-for-testing-full-14.log`、Release `ui/release-final.log` 成功；最终 Release `codesign --verify --strict --deep` 通过。 |
| 可重建 fixture | `verify-server.py --prepare-ui` / `--stop-ui` 实际运行通过，检查 0700 目录、0600 配置、readyz、指定 PID 停止及端口关闭；默认 Swift API 契约再次通过，`ui-contract-final/api-smoke-report.json`。 |
| 大数据列表适配 | 项目列表改用 `include_summary=false`；真实 Swift API 验证空摘要、完整路径/状态/时间、63 runs 分页及筛选通过，`metadata-contract/api-smoke-report.json`。Debug `ui/build-metadata.log`、Release `ui/release-metadata.log` 编译成功，Release 签名校验通过。 |

测试日志、xcresult 和录屏可能包含临时密码片段，按私有产物管理，不公开分享。选定的页面截图位于 `screenshots/native-*.png`；可重建环境与运行方法见 [development.md](development.md)。App 不内置 QA 账号。

未提供 Apple 签名 Team / 真实 Bundle ID / APNs 私钥与真机，因此尚未验证真机 APNs token、Apple 实际投递和通知点击。系统 OAuth 代码/PKCE 已实现，外部 GitHub/OIDC 账户的系统认证浏览器交互也仍待配置后实测。

## 2026-10-25 · 工作流与原生关注

本轮产物位于 `outputs/ios/workflow-native`，独立工作树 `codex/workflow-native`。

| 验证 | 结果与证据 |
| --- | --- |
| B07 / B08 Core | 结构化时间默认值、纳秒范围、稳定事件身份、真实 Step；目录权限/超时/上限隔离、局部重试与取消旧响应通过。`core-b07-b08.log`。 |
| B07 真实 HTTP | 从服务端 `a7e2a12` 隔离构建；63 runs / 通知和原有契约全通过。文本、表格、媒体各 23 条跨两页，21 条无 Step；重复时间、纳秒闭区间和显式 Step 过滤通过。`b07-b08-api/api-smoke-report.json`。 |
| 关注 Core / transport | 关注意图、分页、版本冲突、旧列表、离线恢复、不确定成功、快速反向点击、同/不同账号重登录隔离、Keychain 失败和 incarnation 隔离通过；条件请求头、完整查询身份 pin 与小趋势预算通过。`core-native-frozen.log`：38 项，1 个真实 HTTP opt-in skip。 |
| 集成 HTTP | `mlboard-integrated` 的双会话关注、3 条完整分页、相反修改 412、错误 incarnation 404、项目订阅不变通过；40 点小趋势与错误 incarnation 历史 404 通过。包含 B07 与全部既有 HTTP 契约，`integrated-api-02/api-smoke-report.json`。初轮仅把错误 incarnation 预期从 409 对齐后端隐私语义 404。 |
| 大配置关注分页 | 从服务端冻结提交 `1366282` 精确快照构建，完整 HTTP 契约两轮通过。另建 33 个配置均为 65,536 字节的实验，原生默认页成功解码；7 条一页共五页完整、无重复且版本稳定，最新一轮最大实测页体 5,402 字节。关注 GET/PUT/list 都是空配置轻投影，独立详情仍有完整配置。`following-large-config-02/api-smoke-report.json`、`server-contract-tests.log`；二进制 SHA256 `28e94c17c2e741a31f6d54b8ae4c10c6927eb42b117ced3721bccac5a1610ae4`。Core `core-large-following.log` 仍为 38 项、1 个 opt-in skip、0 失败。 |
| 模拟器编译 | 最新 Debug build-for-testing 与 Release ad-hoc 构建通过；两包签名校验通过，Release 无 HTTP 放行且 APNs 为 production。`build-navigation-identity.log`、`build-navigation-identity-release.log`。 |

`test06FollowingAndRecordsWithoutStep` 已编译，新增页面的 XCUITest 与中英文/明暗/Dynamic Type 视觉验收尚未执行。用户已允许 CoreSimulator 系统日志路径例外，并明确要求锁屏期间先完成实现、稍后再测 UI；本轮没有启动设备。待用户解锁后独立验收，历史 UI 通过记录只代表对应的旧版本。

## 2026-10-25 · 最新手机版设计对齐

独立工作树 `codex/workflow-native-alignment`，基于 `792a70d`；对应关系与刷新边界见 [workflow-alignment.md](workflow-alignment.md)。产物均在 `outputs/ios/workflow-native-alignment`。

| 验证 | 结果与证据 |
| --- | --- |
| Core | `core-final.log`：41 项、1 个真实 HTTP opt-in skip、0 失败。新增真实标量目录选择、context 身份、精确 `summary.last` / 迟到低 Step / 非有限值测试；不从 Step 曲线末点推导最新值。 |
| 通用 SDK 构建 | Debug `build-alignment.log` 成功；最终 `build-for-testing-alignment.log` / `.xcresult` 为 `TEST BUILD SUCCEEDED`，含原生 UI runner 的编译。`CODE_SIGNING_ALLOWED=NO`，不代表可安装签名或已执行 UI 测试。 |
| 待执行交互 | 更新验收断言：曲线首屏、参数次级入口、通知系统返回与完整分页保留、原生通知 switch、快速关注不进入详情且不改变比较选择。 |

本轮没有启动模拟器、原生 UI 或 XCUITest，也没有重复运行需要隔离 API fixture 的可选 HTTP 测试。系统返回/菜单实际点击、列表滚动保留、开关的布局及中英/明暗/Dynamic Type 验收，等用户解锁后执行；历史 UI 记录不替代本版本验收。

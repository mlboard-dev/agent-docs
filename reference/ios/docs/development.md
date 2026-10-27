> 来源：[ios/docs/development.md](https://github.com/mlboard-dev/ios/blob/d42eab1f37a90c5d171611f57556877f62e39fda/docs/development.md) · `d42eab1`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 原生 iOS 开发

## 工程与构建

最低 iOS 17，Xcode 15+，已在 Xcode 27 / iOS 27 SDK 验证。工程使用系统框架，不安装全局依赖。`App/` 为 SwiftUI 页面和 iOS 生命周期；`Sources/MLBoardCore/` 为 URLSession API、查询契约和保留整数精度的数据适配。Xcode app 与 SwiftPM tests 编译同一组 core 源文件。

从 mlboard 工作区根目录运行，缓存与产物均放在根内；不重设 `HOME`：

```sh
IOS_OUTPUT="$PWD/outputs/ios"
mkdir -p "$IOS_OUTPUT/tmp" "$IOS_OUTPUT/cache/clang" "$IOS_OUTPUT/cache/swift"
TMPDIR="$IOS_OUTPUT/tmp" \
CLANG_MODULE_CACHE_PATH="$IOS_OUTPUT/cache/clang" \
SWIFTPM_MODULECACHE_OVERRIDE="$IOS_OUTPUT/cache/swift" \
swift test --package-path src/ios --scratch-path "$IOS_OUTPUT/swift-build" \
  --cache-path "$IOS_OUTPUT/cache/swiftpm" --config-path "$IOS_OUTPUT/cache/config" \
  --security-path "$IOS_OUTPUT/cache/security"

TMPDIR="$IOS_OUTPUT/tmp" \
CLANG_MODULE_CACHE_PATH="$IOS_OUTPUT/cache/clang" \
xcodebuild -project src/ios/MLBoard.xcodeproj -scheme MLBoard \
  -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath "$IOS_OUTPUT/DerivedData" \
  -clonedSourcePackagesDirPath "$IOS_OUTPUT/SourcePackages" \
  -resultBundlePath "$IOS_OUTPUT/build-debug.xcresult" CODE_SIGNING_ALLOWED=YES CODE_SIGN_IDENTITY=- build
```

模拟器运行必须保留 ad-hoc 签名，`CODE_SIGNING_ALLOWED=NO` 只产生可编译的 unsigned 包，安装后 Keychain 会返回 `-34018`，无法登录。`Config.xcconfig` 已对 simulator 默认启用 ad-hoc；不需要 Apple Team 或证书。

Release 可用同一命令，将 configuration 改为 Release，并使用单独的 `DerivedData-release` 目录。新增 Swift 源文件后运行 `python3 src/ios/scripts/generate-project.py`；该脚本重建项目文件、共享 scheme 与两种 Info.plist。

Core 测试包括响应体硬上限及底层流取消、Cookie/Origin/CSRF、403 会话识别、并发请求上限、严格查询字段、超限 run 拒绝、Int64 坐标、缺失值断线、结构化事件精度与通知引用校验。`ServerContractTests` 默认跳过，避免使用任何现有账户。

账号关注使用独立 API、Keychain 待同步意图和原生页面，版本及冲突规则见 [following.md](following.md)。Core 回归包含快速反向点击、离线恢复、不确定成功、412 人工确认、旧列表响应、注销/换号和 Run 删除重建。前台重验证不等待趋势数据。

项目实验列表请求 `include_summary=false`，仅读取路径、状态、时间等元数据，避免打开列表时扫描每个实验的长历史；实验详情及图表仍按需读取。真实 API 契约覆盖该模式下 63 个实验的完整分页及筛选。

实验详情的元数据、指标目录、最新值摘要和文件目录分别管理加载、失败与取消状态。元数据使用 `include_summary=false`；摘要或文件失败不阻止指标目录出现。文件目录仅在打开“文件”时读取；权限、超时或 1,000 文件的服务端目录上限只影响文件区域，可单独重试。刷新失败保留上次成功数据，权限撤销或资源删除则清除相应缓存；切换实验、账户或退出页面会使在途旧响应失效。

对新建的隔离 SQLite 实例验证真实 HTTP 契约：

```sh
python3 src/ios/scripts/verify-server.py --binary "$PWD/outputs/bin/mlboard-audit"
# 验证本轮支持 Following 的服务端二进制时，追加 --following。
```

该脚本清除继承的部署/SDK/S3/APNs 环境配置，选随机 loopback 端口，仅在 `outputs/ios` 下创建并销毁测试数据。它创建 63 个真实测试实验和 63 条通知，使用 Swift 客户端验证完整分页、三实验查询、鉴权文件下载和会话注销；报告包含实际二进制路径与 SHA256。临时凭据仅保存在权限为 0600 的测试文件中，结束后删除，不打印。

`--following` 另在独立临时项目创建 33 个各含 65,536 字节配置的实验并关注。验证原生默认页仍在 2 MiB 传输限制内、每页 7 条共五页完整且不重复、实测 HTTP 页体不超过 1 MiB、卡片为空配置的轻投影，而独立详情保留完整配置。此附加项目随后删除，不改变 UI fixture。

默认 API 契约模式保留三点 Int64 极值与缺失点数据，用于验证精度和断线。UI 验收使用下面的 `--prepare-ui` 模式，曲线改为三组各 60 步的 loss / accuracy，同时保留缺失点。

## 模拟器验收

不要使用用户默认设备集。已有系统 runtime 可以读取，专用设备与截图留在工作区：

```sh
mkdir -p "$IOS_OUTPUT/simulators"
xcrun simctl --set "$IOS_OUTPUT/simulators" create MLBoard-QA \
  com.apple.CoreSimulator.SimDeviceType.iPhone-17 com.apple.CoreSimulator.SimRuntime.iOS-27-0
# 后续命令均指定同一个 --set 和创建命令返回的 UDID。
xcrun simctl --set "$IOS_OUTPUT/simulators" boot '<UDID>'
xcrun simctl --set "$IOS_OUTPUT/simulators" install '<UDID>' \
  "$IOS_OUTPUT/DerivedData/Build/Products/Debug-iphonesimulator/MLBoard.app"
xcrun simctl --set "$IOS_OUTPUT/simulators" launch '<UDID>' org.example.mlboard
xcrun simctl --set "$IOS_OUTPUT/simulators" io '<UDID>' screenshot "$IOS_OUTPUT/login.png"
```

Debug 包提供独立 Keychain 运行探针，不修改会话、连接后端或操作 UI：分别带 `--keychain-probe-write` 和 `--keychain-probe-read-delete` 启动应用，中间 terminate 一次。结果位于 app data container 的 `Library/Caches/MLBoardDiagnostics/keychain-write.json` 与 `keychain-read-delete.json`；应验证 `read_after_write`、`persisted_across_launch`、`removed` 和 `passed` 均为 true。可用带同一 `--set` 的 `simctl get_app_container '<UDID>' org.example.mlboard data` 获取根内路径。Release 不包含该探针。

使用自己的实际服务器登录；本地隔离服务器需打开登录页的 Debug HTTP 开关。验收组织/项目、至少两页实验、文件夹与搜索、配置、曲线点检、三实验比较、结构化记录、收件箱第二页、订阅、重试和退出。切换暗色与中文，检查较大动态字体。截图中的 QA 数据必须明确来自临时测试服务器。

## 签名与 APNs

1. 复制 `Config.local.example.xcconfig` 为 `Config.local.xcconfig`，填真实 `DEVELOPMENT_TEAM` 和 `PRODUCT_BUNDLE_IDENTIFIER`，此文件已忽略。
2. 在 Apple Developer 中创建同 Bundle ID 的 App ID，启用 Push Notifications，使用匹配的 provisioning profile。真机需要可用的开发者签名；模拟器编译无需 Team。
3. Debug 默认 `APNS_ENVIRONMENT=sandbox`，Release 默认 `production`。可在本地配置覆盖，值必须与签名的 `aps-environment` entitlement 以及服务器配置一致。
4. 服务器配置 `MLBOARD_APNS_ENABLED`、Team ID、Key ID、topic、environment 和 `.p8` 文件路径。私钥只放服务器；不要把 `.p8`、证书、密码或 session token 放入 app、Info.plist、xcconfig 或源码。
5. 应用中打开项目铃铛订阅完成/失败/停止事件，再在设置中启用通知。授权成功后向系统注册 token，并将 installation ID、token、environment、topic、locale、preview 发给自己的服务器。
6. 设置中发送测试只表示入队，刷新设备状态确认 `accepted` / `failed`。Apple 接受请求与真机收到横幅仍是不同的验证结果。通知点击会先重新鉴权，再按通知 ID 从服务器获取真实目标，最后读取实验确认权限。

没有 Apple Team / Bundle ID / APNs 私钥时，仅验证原生编译、模拟器页面和本地 API/队列契约；真机授权、token 获取、Apple 实际投递与通知点击仍需签名设备验收。应用没有后台轮询、静默推送或后台刷新任务。

## 数据、隐私与边界

- 单个实例、单个登录账户。切换实例先退出；推送不携带可导航的服务器 URL。通知 ID 在当前已配置实例读取并复验 ACL，旧实例的通知不会触发任意网络跳转。
- 会话 Cookie token、CSRF、待注销操作和账号关注待同步意图只存 Keychain（`WhenUnlockedThisDeviceOnly`）。密码不保存，APNs token 仅保留在内存中，每次系统回调更新服务器。UserDefaults 仅放服务器地址、语言和通知开关。
- 退出或设备注销先禁止并等待取消在途注册。网络失败时将原实例/原会话/installation 的待撤销操作保存在 Keychain，应用前台恢复时重试，每次最多两条；设置可手动重试。最多保留 32 个待撤销项，不会静默丢弃旧操作。同实例同用户未完成撤销前不能重新启用推送。
- API 不跟随重定向；所有实例合计最多两个数据读取请求，并为登录、注销、关注和元数据操作保留一个独立请求位置；两类队列各最多等待 16 个请求，队列满时明确报错，取消会释放等待位置。JSON 上限 2 MiB，文件预览上限 8 MiB；文本文件预览另限 2 MiB。流超限或取消时显式取消底层 URLSession task。
- 数据查询、含摘要的 Run 读取、数据目录和文件内容使用独立 session：默认请求空闲期限 900 秒、整个传输期限 960 秒，容纳服务端最高读取期限、权限复核和响应写入预算；实际通常仍按实例的较短预算完成或失败。控制请求保留 20/30 秒；显式 `URLSessionConfiguration` 中更短的期限对两类请求均生效，注销重试仍为 8/12 秒。请求可以取消，切页或退出不需等待长期限结束。
- 实验和通知按服务端 cursor 手动继续分页，直到 `next_cursor` 为空；不会把第一页当成完整结果。列表空态与失败/重试分开显示。
- 标量最多三个实验、每实验 1,000 点；服务端扫描预算 1,000,000 点、2 MiB；新查询省略 `timeout_ms`，继承实例读取期限。范围筛选可缩小过大的查询。主 producer、所有 session、`latest_logical` 重复步数策略与当前 Web 默认语义一致；暂未提供 worker producer 手动选择。
- Int64 坐标先减去精确整数原点后绘图，点检保留原字符串；跨度超过 Double 可精确表达的整数范围时，明确切换为坐标顺序轴并警告。null / 非有限值划分线段，额外点或 series 不会无提示隐藏。
- 结构化查询默认按事件时间 `wall_time`，包含没有 Step 的文本、表格和媒体。可改用 Step、Epoch、耗时、样本数等坐标；其他坐标只包含实际记录该坐标的事件。范围起止均包含边界，时间直接传 RFC3339 字符串，保留纳秒精度；只在事件实际有 Step 时显示 Step。事件身份区分同一时间的记录，并在分页间保持一致。
- 结构化查询每页 20 条、每次最多 500 条，快照保持稳定；过大时显示预算错误并允许缩小范围。失败的翻页保留已确认页面，重试继续请求失败页。直方图最多合并为 128 根柱；混淆矩阵一次显示最多 20 个匹配类别，归一化使用全体类别；超过 1,000 点的结构化曲线保留原始记录而不错误抽样。JSON 树按 100 项逐批展开。
- 图片用 ImageIO 缩略到 1,600 像素；PDF 用 PDFKit，音视频用 AVKit 的已鉴权本地文件。临时文件采用完整文件保护、禁止备份，关闭预览、退出或下次启动时清理；不把任意记录 URL交给浏览器渲染。

## XCUITest 原生交互验收

`MLBoardUITests` 是独立测试 runner target，使用真实 `tap`、`typeText`、`swipeUp` / `swipeDown` 与系统导航。App 只增加无业务副作用的 accessibility identifiers；测试不调用 App 内部方法、不写 Keychain/session、不注入路由，也不替换 API。测试只接受 loopback 隔离服务器和超过 50 条的实验/通知；QA fixture 从 runner 环境读取，不传给被测 App。

测试必须使用临时可丢弃账号。XCTest 的 `typeText` 活动日志可能记录密码片段，SecureField 也不能视为日志脱敏保证；测试日志与 xcresult 都属于敏感临时产物，不能公开分享。

先通过仓库中的脚本准备专用 UI 服务器，不依赖 outputs 中的临时脚本：

```sh
python3 src/ios/scripts/verify-server.py --binary "$PWD/outputs/bin/mlboard-audit" --prepare-ui
# 将上一步输出的两个路径填入；每次创建新的随机目录，不覆盖已有实例。
UI_FIXTURE="$IOS_OUTPUT/ui-qa-<随机标识>/ui-credentials.json"
UI_INSTANCE="$IOS_OUTPUT/ui-qa-<随机标识>/instance.json"
```

此模式不运行 Swift 测试。它启动只监听 `127.0.0.1` 的独立 SQLite 服务，经公共 API 创建 63 个实验与 63 条通知、`training/v1/seed-01..03` 的各 60 步标量、原生直方图/文本和实际曲线 PNG。账号、数据库、文件与日志均在新的 0700 工作目录内；凭据与实例 metadata 使用 0600。终端仅输出 URL、PID 与文件路径。只有准备全部成功才保留服务，并使用独立进程 session，命令结束后可继续测试；失败会停止服务并清理新建目录。

先仅编译，不执行 UI 自动化。下面的自定义设备集参数已在 Xcode 27 核验；始终显式给出根内 result bundle，避免 Xcode 失败时写默认临时路径：

```sh
umask 077
mkdir -p "$IOS_OUTPUT/ui"
chmod 700 "$IOS_OUTPUT/ui"
TMPDIR="$IOS_OUTPUT/tmp" CLANG_MODULE_CACHE_PATH="$IOS_OUTPUT/cache/clang" \
xcodebuild -project src/ios/MLBoard.xcodeproj -scheme MLBoard \
  -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
  -DVTSimulatorSetLocation="$IOS_OUTPUT/simulators" -parallel-testing-enabled NO \
  -derivedDataPath "$IOS_OUTPUT/DerivedData-ui" -clonedSourcePackagesDirPath "$IOS_OUTPUT/SourcePackages-ui" \
  -resultBundlePath "$IOS_OUTPUT/ui/build-for-testing.xcresult" build-for-testing

python3 src/ios/scripts/prepare-ui-tests.py \
  --xctestrun "$IOS_OUTPUT/DerivedData-ui/Build/Products/MLBoard_iphonesimulator27.0-arm64-x86_64.xctestrun" \
  --fixture "$UI_FIXTURE" --manifest "$IOS_OUTPUT/ui/run.json"
```

`ui-credentials.json` 必须权限为 0600，包含 `server`、`username`、`password`、`project_id`、三个 `run_ids`、`run_count`、`notification_count`。测试项目需有 `training/v1/seed-01..03` 路径、`loss` 标量、`weights` 直方图、`optimizer: AdamW` 配置与 `chart.png` 文件。fixture 不提交，prepare 脚本也不打印其值。私有 `.xctestrun` 在原构建产物旁生成，以保持 `__TESTROOT__` 路径有效；其 `EnvironmentVariables` 只供 runner 使用，`UITargetAppEnvironmentVariables` 留空。

用户明确授权 UI 自动化后，先执行最小登录→项目→首屏 50 runs 用例：

```sh
TMPDIR="$IOS_OUTPUT/tmp" xcodebuild \
  -xctestrun "$IOS_OUTPUT/DerivedData-ui/Build/Products/MLBoard_iphonesimulator27.0-arm64-x86_64-private.xctestrun" \
  -destination 'platform=iOS Simulator,id=<专用设备 UDID>' \
  -DVTSimulatorSetLocation="$IOS_OUTPUT/simulators" \
  -parallel-testing-enabled NO -maximum-concurrent-test-simulator-destinations 1 \
  -only-testing:MLBoardUITests/NativeAcceptanceTests/test01LoginAndProjects \
  -resultBundlePath "$IOS_OUTPUT/ui/login-projects.xcresult" test-without-building
```

完整验收改为 `-only-testing:MLBoardUITests/NativeAcceptanceTests/test02ExperimentWorkflow`，并使用新的 result bundle 路径。它实际滑动并点击分页至 UI 显示完整预期数量，再验证文件夹/搜索、三个实验比较、配置、单实验曲线、原生直方图、鉴权 PNG、订阅持久化、收件箱点击重新鉴权导航、中英切换及跨启动退出。截图使用 `XCTAttachment` 保存在 xcresult；失败也保存截图。订阅测试会恢复原选择，但依旧应仅对可丢弃 QA 实例执行。

`test04SessionRestoresWithoutNotificationGate` 通过真实 UI 登录后 terminate / launch，要求 10 秒内恢复到关注首屏，再切项目实际读取实验并注销；冷恢复阶段不会重新登录。`test03ChineseLargeTypeVisual` 用于操作员已将专用模拟器设为浅色和较大辅助字体后的中文布局验收，实际查看三条实验、单图和三实验曲线及底部比较操作，不重复遍历 63 条数据。两者同样通过 `-only-testing` 选择，并各用新的 result bundle；字体与外观在结束后恢复原值。

`test05HistogramBars` 从真实登录进入直方图，保存零基线柱形截图供人工复核。测试在大字体下使用原生三击选择整段文本、键盘提交和滚动；输入后核验完整文本，不能假定点击总会把光标放到末尾。Toggle 点击内部开关并先断言状态改变，避免把点中行空白误判为保存失败。

`test06FollowingAndRecordsWithoutStep` 需要本轮支持 Following / incarnation 的服务器。它从项目列表星标，检查比较选择未变化，再从关注卡片用系统导航进入实验；文本、表格、媒体三种记录分别翻到第二页，取消关注后撤销，再重启验证持久状态并注销。fixture 通过真实 API 生成每种 23 条混合记录（21 条无 Step），重复纳秒时间下仍有独立事件身份；HTTP 契约另验证精确时间范围与显式 Step。此用例仅编写或编译不代表已执行，实际结果单独记录在 [verification.md](verification.md)。

`.xctestrun` 包含 runner 环境中的临时凭据，测试日志及 xcresult 还可能包含输入密码片段。目录使用 0700、配置/日志/结果内普通文件使用 0600；执行前设置 `umask 077`。不要打印、提交或公开分享这些敏感产物；读取失败日志时必须整行脱敏涉及 `passwordField` 或安全输入的 `typeText` 记录。执行完删除 `*-private.xctestrun`；若需要重试，重新 prepare。不要并行运行多个 UI 测试或在测试期间用其他工具争用同一模拟器。

Xcode 27 在该自定义设备集上曾复用已失效的 `testmanagerd` socket 路径，使测试在 App 启动前失败。若日志明确为此错误，可仅重启本任务专用 UDID（同一 `simctl --set` 下 shutdown → boot → bootstatus），再以新的 result bundle 路径重试；不要触碰用户默认设备集。此类启动失败不能记为 App 交互已执行。每轮应先检查测试是否真正进入用例，再分别记录断言失败、页面缺陷与 harness 故障。

验收结束后只停止 metadata 记录的专用服务器：

```sh
python3 src/ios/scripts/verify-server.py --stop-ui "$UI_INSTANCE"
```

停止命令先校验 metadata 位于工作区内，并用 `ps` 核对 PID 的完整启动参数与该实例的数据目录；PID 被复用或参数不匹配时拒绝发送信号。它只向该 PID 发送 TERM，10 秒未退出且身份仍一致时再发送 KILL，不按名称停止其他服务。该命令保留数据与日志供检查；确认测试已结束后，可删除 metadata 中的工作目录、私有 `.xctestrun` 与敏感结果。不要用进程名批量停止服务，也不要删除正在验收的其他实例。

## Config 数字与无损传输

`JSONValue.decodeHTTP` 只在 config 子树保留 `ExactJSONNumber` 原词元；标量曲线和账户字段保持原来的 `.number(Double)` 语义。Config 数字通过 `.exactNumber` 与 `.string` 区分，`.text` 显示完整词元，`encodedData()` 发回裸 JSON number。不要用普通 `JSONDecoder`/`JSONEncoder` 重保存精确 config；这些路径会明确抛错，避免静默舍入或转成字符串。普通账户/指标 Codable 不受影响。

API 对显式 config 写入验证 64 KiB、20 层、4096 节点，并声明 `MLBoard-Config-Numbers: exact-v1`。不安全 Double 整数须从原始 JSON 用无损边界读取；客户端不能恢复调用前已舍入的数字。读取/导出旧数据有独立字节/节点预算和迭代深度限制。数学等值与词元形式不同，原导出保留 `1.00` 等词元。

`ConfigPrecisionTests` 覆盖 ±2^53 邻值、int64 边界、嵌套/指数/数字字符串、普通 Codable 兼容和 3000 层 legacy 读取。设置 `MLBOARD_CONFIG_TEST_FIXTURE` 为工作区内独立 loopback fixture 后，还会真实执行创建、幂等重放、GET、列表、metadata PATCH、config 重保存与导出；无 fixture 时该真实 HTTP 用例显式跳过。原生 UI 仍需解锁后的独立交互验收，core/build 成功不代表已验收 UI。

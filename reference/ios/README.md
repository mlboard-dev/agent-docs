> 来源：[ios/README.md](https://github.com/mlboard-dev/ios/blob/d42eab1f37a90c5d171611f57556877f62e39fda/README.md) · `d42eab1`。链接已整理；勘误及示例泛化见[来源说明](../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# MLBoard iOS

独立 Git 仓库中的原生 iOS 客户端，最低 iOS 17。使用 SwiftUI、Swift Charts、UserNotifications、AuthenticationServices 和 Keychain；没有 WebView，也不依赖第三方包。

- 密码登录，以及系统认证浏览器中的 GitHub / OIDC OAuth + PKCE。
- 组织与项目、路径文件夹、服务端搜索/状态筛选、完整实验分页。
- 账号级关注首屏、项目与详情星标、原生趋势卡片；跨设备同步与项目通知订阅独立。
- 实验首屏原生曲线、真实最新指标与独立趋势、次级参数入口、六种横轴、最多三个实验比较。
- 原生直方图、混淆矩阵、ROC / PR / XY 曲线、表格、文本，以及鉴权的图片 / PDF / 音视频文件预览。
- 完整通知分页与来源返回、独立系统通知开关、项目状态订阅、设备管理与 APNs 注册/注销/测试。
- 中英文切换、跟随系统的明暗外观、动态字体。

打开 `MLBoard.xcodeproj`，选择 `MLBoard` scheme。共享的网络与数据处理模块位于 `Sources/MLBoardCore`，可用 SwiftPM 在 macOS 运行测试。工程生成器是 `scripts/generate-project.py`，不需要 XcodeGen。

构建、模拟器隔离、签名、真机推送和验证说明见 [docs/development.md](docs/development.md)。服务器契约见 server 仓库的 `docs/mobile-api.md`、`docs/apns.md`。

关注的版本、离线与冲突规则见 [docs/following.md](docs/following.md)；需要支持 `run_incarnation` 和 Following API 的服务端。

手机版最新设计的对应实现与验证边界见 [docs/workflow-alignment.md](docs/workflow-alignment.md)。

应用一次连接一个服务器和一个账户；所有业务数据来自该服务器的公共 API，应用不包含演示账号或内置实验。生产环境要求 HTTPS。本地 HTTP 仅在 Debug 中显式开启，且只允许 loopback、私有 IPv4 或 `.local` 地址。

Apple Team、真实 Bundle ID、APNs `.p8` 私钥和设备配置由部署者提供。仓库中的 `org.example.mlboard` 是签名占位值；未提供 Apple 凭据时不能声称已完成真机 APNs 投递验证。

> 来源：[server/docs/realtime-cluster.md](https://github.com/mlboard-dev/server/blob/4caeb73c2e0697158c5f376de000da3e6d523d78/docs/realtime-cluster.md) · `4caeb73`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 可选跨实例实时提示

`MLBOARD_REALTIME_BUS_URL`（或 `--realtime-bus-url`）默认空，关闭跨实例提示。启用时填写私有 Valkey 的 `redis://:password@host:6379/0`；TLS 使用 `rediss://` 并校验证书。它独立于 query cache 开关/URL，不保存会话或权限。所有应用实例须共享同一 SQL 数据库及 storage epoch；恢复数据并轮换 epoch 后应重启应用实例。频道为 `mlboard:realtime:v1:<epoch 摘要>`，不同数据库隔离。

实例间只发送项目失效提示，接收方给已订阅相应项目的 SSE/WebSocket 发送 `reset_required`，客户端按当前权限重取数据。消息不含 Run、Dashboard、用户或实验数据。私有 following/dashboard 更新仍使用现有 SQL user_events，不进入项目广播。鉴权、受限 Run grant、撤权检查均不因 bus 放宽。

发布位于后台，写入 ACK 只入本地队列，不等待 Valkey。队列合并最多 256 个项目；队满退为整体 reset，最多跟踪 128 个来源。丢序号、格式异常、发布不确定、订阅断开/重连均显式要求核对。RESP2 在分配前限制 bulk 长度，hint 最多 1 KiB；发布 IO 最长 500ms，订阅 PING 每 5s、无响应最长 15s 后重连。仅使用 AUTH、SELECT、PUBLISH、SUBSCRIBE、PING，可将 Valkey ACL 限于上述命令及频道前缀。

**这是尽力而为的失效提示，不保证 durable 事件投递。** 进程可能在 SQL COMMIT 后、第一条提示发出前崩溃，序号缺口无法证明这种末条丢失。因此启用时每实例还会每 27–30s（小抖动）对本实例活跃订阅按项目合并发 reset；不读取或轮询未被观看的项目。健康提示通常即时，异常末条可能需约 30s 才核对。补偿会增加客户端按权限重取的读请求：每条活跃连接每周期至多一次 reset，具体 HTTP reads 取决于页面；512 条连接的保守上界约为每秒 19 条 reset。默认关闭，常规性能矩阵也保持关闭，收益/额外读需单独测量。

启用时 cursor 为 `instance 域.本地序号`，只用于该实例的有限回放；切换实例、旧数字 cursor 或模式回退会要求 reset，不能把本地序号当成全局日志。客户端应原样保存 cursor 并处理 reset。默认关闭时维持旧数字 cursor。

管理员状态的 `realtime_bus` 只提供开关、待处理项目数、overflow/reset/error 计数，不提供 URL/凭据。服务关闭会取消发布、关闭订阅并等待 worker；Valkey 不可用不会阻止启动和 durable SQL ACK。若需要持久事件日志，应另行评估事务 outbox 的写放大、保留和按实例消费，不将此可选提示误当持久队列。

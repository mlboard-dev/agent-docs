> 来源：[server/docs/request-boundaries.md](https://github.com/mlboard-dev/server/blob/4caeb73c2e0697158c5f376de000da3e6d523d78/docs/request-boundaries.md) · `4caeb73`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 请求、配置与上传边界

Run config 创建和显式 PATCH 同时限制为 65,536 个编码字节、深度 20、4,096 个 JSON 节点。根对象深度为 0，每个对象、数组及标量（含 null）计一个节点。校验不转换 `json.Number`，保留大整数、小数正文和创建幂等 hash。已有深配置不重写；相同原始内容的创建重试、不修改 config 的 PATCH 继续有效。新建及显式替换 config 超限返回 422。

普通 JSON body 默认在 30 秒内读完，包括确认单一文档的 EOF；query、公开 query 和 MCP 也使用此可配置的接收保护。数据读取默认 60 秒，配置 `MLBOARD_READ_TIMEOUT_SECONDS` / `--read-timeout` 可取 1..600 秒，显式更短 query 预算及父 context 优先。分享预览独立最终权限复核默认 10 秒，可通过 `MLBOARD_READ_RECHECK_SECONDS` / `--read-recheck-timeout` 配置为 1..120 秒。有限响应从开始写出起默认有 60 秒预算，不消耗数据工作或合法上传接收时间；预算覆盖最后一次 flush，在下一次请求开始时重置。SSE/WS URL 的认证、权限、游标或握手拒绝同样受此写期限约束；只有成功的 SSE 或 WebSocket 升级后使用流自身策略，WebSocket 握手写出后清除握手期限。JSON 接收或上传总时限超时返回 `408 request_timeout`；数据读取/查询预算耗尽返回 `422 query_timeout`；连接已不能写时由客户端观察断开。

有请求体时，在鉴权/路由/Content-Type 检查前即启用默认接收保护，避免 net/http 自动清理未读 body 时把 401/415/404 等原错误响应无限阻塞。只有上传鉴权通过且取得账号/项目/全局额度后，才升级为上传时限；SSE/WS 的正常无 body 请求不套此短读取期限。

文件下载独立于普通 JSON 的 60 秒写期限：初次鉴权后，对象打开及读取共用默认 600 秒总 context；只有对象打开、最终 Run/share 身份复核通过且实际返回带文件正文的 GET 200/206 时，才启用默认 30 秒写出停滞期限。每次成功写出可刷新停滞期限，固定总截止不续期，最后 flush 仍受两者限制。父 context 或已有更短写截止优先。HEAD、空文件、304、416、未授权、对象不存在及其他错误仍使用普通有限响应策略，不能通过 URL 提前取得长写期限。S3 GetObject 在存在明确 context 截止时沿用该总截止，无截止调用仍保留旧 2 分钟客户端限制；HEAD/PUT/Delete 不变。超时/取消中断源读取和阻塞写出，由 handler 关闭对象；截止监控退出后才允许连接用于下一请求。

上传总时限默认 600 秒（含对象发布），读取停滞默认 30 秒；仍接受最多 256 MiB 的单文件。并发同时限制为全实例 8、每账号 2、每项目 4，额度一次取得，失败返回 `429 artifact_busy` 与 Retry-After。Body 超时、断开、存储错误及冲突释放额度并删除暂存文件。上传开始固定 project/run/incarnation；读取期间删除重建的 Run 无法接收旧上传，正常数据 revision 增长不影响上传。

对象 IO 保持在 SQL 事务外。失败提交后先确认对象没有持久引用再删除；数据库不能确认时保留对象。删除有有限重试和警告日志，持续存储故障仍需管理员清理确认未被引用的孤立对象。未改变 durable ACK、下载身份复核、HTML sandbox、Range 或 S3 完整性语义。

登录、注册、初始化和密码操作保留全局两个 Argon2 计算槽位；来源每分钟最多 30 次，同一来源与账号组合每分钟最多 10 次。不同来源不共享账号锁；真实 NAT 后的用户仍共享来源额度。桶有过期与 LRU 淘汰，总计最多 4,096 项，账号键只保留摘要。未知账号仍执行等价密码计算，不改变统一凭据错误。

可信代理默认关闭。配置 CIDR 后只在 socket 对端匹配时接受 `X-Forwarded-For`，从右向左剥离可信 hop，最多 16 个地址/2,048 字节；畸形链返回 400。边缘代理必须清除外来头或追加真实 socket 来源。`Forwarded`、转发 Host/Proto 不参与此地址策略，不改变 PublicURL、Host、Origin、CSRF 的规则。配置值见 [configuration.md](configuration.md)。

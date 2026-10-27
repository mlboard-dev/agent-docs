> 来源：[server/docs/configuration.md](https://github.com/mlboard-dev/server/blob/4caeb73c2e0697158c5f376de000da3e6d523d78/docs/configuration.md) · `4caeb73`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 配置来源与生效时间

有对应命令参数的运行配置按 **CLI > 环境变量 > 默认值** 取值；例如 `--database sqlite` 覆盖 `MLBOARD_DATABASE=postgres`。每一项独立取值：改变数据库类型时也要提供该数据库对应的 DSN。程序不自动读取 `.env`；Compose 示例通过插值将受支持的变量明确传入容器。

## 运行配置：重启读取

| 环境变量 | 命令参数 / 默认行为 |
| --- | --- |
| `MLBOARD_LISTEN` | `--listen`；二进制默认 `127.0.0.1:8080`，镜像默认 `0.0.0.0:8080` |
| `MLBOARD_DATABASE` | `--database`；默认 `sqlite`，支持 `postgres` |
| `MLBOARD_DSN` | `--dsn`；SQLite 未设置时为 `<data-dir>/mlboard.sqlite3`；PostgreSQL 必须提供 |
| `SQLITE_TMPDIR` | SQLite 专用临时文件目录，必须是绝对路径；未设置时保留 SQLite 的默认目录选择 |
| `MLBOARD_DATA_DIR` | `--data-dir`；二进制默认 `outputs/data`，Compose 为 `/data/files` |
| `MLBOARD_PUBLIC_URL` | `--public-url`；未设置时从监听地址派生，wildcard host 转为 `127.0.0.1` |
| `MLBOARD_TRUSTED_PROXIES` | `--trusted-proxies`；逗号分隔的实际代理 IP CIDR，默认空，转发地址不受信任；只解析 `X-Forwarded-For` |
| `MLBOARD_READ_TIMEOUT_SECONDS` | `--read-timeout`；数据读取默认及查询执行上限，默认 60 秒，范围 1..600 秒 |
| `MLBOARD_READ_RECHECK_SECONDS` | `--read-recheck-timeout`；分享预览独立最终权限复核，默认 10 秒，范围 1..120 秒 |
| `MLBOARD_JSON_READ_SECONDS` | `--json-read-timeout`；默认 30 秒，环境范围 1..120 秒 |
| `MLBOARD_UPLOAD_TOTAL_SECONDS` | `--upload-timeout`；默认 600 秒，环境范围 1..7200 秒，包括存储发布 |
| `MLBOARD_UPLOAD_IDLE_SECONDS` | `--upload-idle-timeout`；默认 30 秒，范围 1..300 秒且不超过总时限 |
| `MLBOARD_RESPONSE_WRITE_SECONDS` | `--response-write-timeout`；默认 60 秒，范围 1..120 秒，从有限响应开始写出计时 |
| `MLBOARD_DOWNLOAD_TOTAL_SECONDS` | `--download-timeout`；已鉴权文件下载默认 600 秒，范围 1..7200 秒，从对象打开开始计时，包含最终 flush；更短的父级截止优先 |
| `MLBOARD_DOWNLOAD_IDLE_SECONDS` | `--download-idle-timeout`；下载成功写出间隔默认 30 秒，范围 1..300 秒且不超过总时限；进展不延长固定总截止 |
| `MLBOARD_UPLOADS_PER_USER` / `MLBOARD_UPLOADS_PER_PROJECT` | `--uploads-per-user` / `--uploads-per-project`；默认 2 / 4，范围 1..8，全局仍为 8 |
| `MLBOARD_WEB_DIR` | `--web-dir`；默认使用内嵌 Web |
| `MLBOARD_SETTINGS_KEY` | 无 CLI；原始 base64 AES-256 密钥，优先于 `<data-dir>/settings.key` |
| `MLBOARD_ARTIFACT_STORAGE` / `MLBOARD_S3_*` | 文件存储与凭据，见 [storage.md](storage.md) |
| `MLBOARD_APNS_*` | 可选原生推送 provider，见 [apns.md](apns.md) |
| `MLBOARD_SUMMARY_PROJECTION` | `--summary-projection`；`off`（默认）、`build`、`on`，见下文 |
| `MLBOARD_CURVE_TREE` | 无 CLI；默认 `0`，`1` 启用版本化范围树构建，派生读取还要求 projection=`on`，见 [query-performance.md](query-performance.md) |
| `MLBOARD_QUERY_PROFILE` | 无 CLI；默认 `0`，`1` 输出低基数请求阶段计时与工作量，压测主组应关闭 |
| `MLBOARD_QUERY_DELTAS` | `--query-deltas`；默认 `false`，可选私有 scalar 帧增量传输，见 [query-frame-reuse.md](query-frame-reuse.md) |
| `MLBOARD_QUERY_CACHE_ENABLED` | 无 CLI；默认 `true`；`false` 关闭查询结果的 L1/L2 缓存与相同 miss 合并 |
| `MLBOARD_QUERY_CACHE_MIB` | 无 CLI；L1 的 key + payload 配额，默认 64 MiB，范围 1–1024 |
| `MLBOARD_QUERY_CACHE_ITEM_KIB` | 无 CLI；单项 payload 上限，默认 2048 KiB，范围 1–8192 |
| `MLBOARD_QUERY_CACHE_TTL_SECONDS` | 无 CLI；L1/L2 TTL，默认 300 秒，范围 1–600 |
| `MLBOARD_VALKEY_URL` | 无 CLI；默认空，仅使用 L1；可选 `redis://` 或 TLS 的 `rediss://` URL |
| `MLBOARD_REALTIME_BUS_URL` | `--realtime-bus-url`；默认空，独立可选的 Valkey 跨实例提示；[一致性/读放大边界](realtime-cluster.md) |
| `MLBOARD_VALKEY_TIMEOUT_MS` | 无 CLI；共享缓存每次操作的超时，默认 20ms，范围 1–250 |

数据工作期限覆盖查询（含最终权限/身份校验和分页快照）、Run 列表/摘要、分类/会话/config/series/events/logs、产物目录及元信息读取，以及公开分享摘要；产物内容下载使用独立下载期限。显式更短的父 context 或客户端取消仍优先。分享预览原有独立复核继续从原请求 context 派生，不继承已耗尽的摘要工作期限，复核超时不返回投影数据。健康检查、队列等待、实时心跳、鉴权和快照清理使用各自原有策略。

`budget.timeout_ms` 可省略；新 Web 查询省略后继承实例的读取默认值。显式正整数预算可更短，但执行时超过实例上限会返回 `422 validation_error`。静态 query/dashboard schema 的可移植上限为 600000ms；保存通过不代表可超出运行实例上限执行。旧 dashboard/导入定义显式保存的 3000ms 等预算保留原值，重新打开、编辑布局或导出不会自动延长；需要延长时应明确编辑该预算或删除此字段。`GET /api/v1/capabilities` 的 `limits.query_timeout_ms` 和 `query_default_timeout_ms` 返回实例实际默认/上限，`share_preview_recheck_timeout_ms` 返回独立复核上限。

JSON body 接收与响应写出各自有限：先完成接收，再执行数据工作，最后从响应开始输出计写期限。提高数据读取时限不会放宽点数、扫描、内存、并发和排队预算。反代还需容纳这些等待，见 [lan-and-proxy.md](lan-and-proxy.md)。

SSE/WebSocket URL 上的认证、权限、游标或握手拒绝仍受有限响应写时限约束。成功的 SSE 响应及已升级的 WebSocket 使用流自身的写策略；WebSocket 握手写出另受 `MLBOARD_RESPONSE_WRITE_SECONDS` 约束，完成后清除该握手时限。

Compose 将容器监听地址固定为 `0.0.0.0:8080`，通过 `MLBOARD_PORT` 配置宿主机端口。留空 `MLBOARD_PUBLIC_URL` 时，Compose 自动生成 `http://127.0.0.1:<MLBOARD_PORT>`；显式公网 URL 优先。`MLBOARD_BIND_ADDRESS` 默认 `127.0.0.1`，对外入口须与 public URL 的 Host/端口一致。Host/Origin 检查始终生效；HTTPS public URL 同时启用 Secure cookie。

SQLite Compose 将 `SQLITE_TMPDIR` 固定为数据卷中的 `/data/files/sqlite-tmp`，避免大型排序耗尽 `/tmp` 的小型 tmpfs。启动时由运行用户创建缺少的目录并检查临时文件写入、关闭与删除；目录不可用会阻止启动。临时文件占用该卷的磁盘空间和 I/O，目录配置须在进程启动前固定，不在连接之间切换；PostgreSQL 忽略此项。

外层工作区的 `scripts/run.sh` 默认保留 `outputs/runtime/mlboard.sqlite` 和 `outputs/runtime/files`，兼容已有实例。显式配置 data-dir 后，由二进制派生该目录中的 SQLite 路径；显式 DSN 优先。使用 PostgreSQL 时 wrapper 不注入默认 SQLite 文件名。

恢复数据库时必须同时恢复原始 `settings.key` 或注入原 `MLBOARD_SETTINGS_KEY`。已有 OAuth 密文缺少原 key、key 格式错误或解密失败都会阻止启动；程序不会生成替代 key 后继续运行。仅修改 bootstrap secret 不能解密已有配置。

## 查询结果缓存与持久投影

每个应用进程的 L1 默认开启，按 LRU 管理，最多 4096 项；配额计算 key 与编码 payload，不是进程 RSS 上限。超单项或总配额的结果仍可在查询预算内返回，但不会写入 L1/L2。错误不缓存，相同 key 的 miss 合并计算。`MLBOARD_QUERY_CACHE_ENABLED=false` 只关闭此查询结果层，不关闭持久投影，也不关闭 Run exact-summary 原有的独立内存缓存（最多 1024 项、合计 8 MiB）。

共享缓存优先使用 Valkey，使用标准字符串命令；`redis://` 是连接协议名，产品名仍为 Valkey。Redis 可作为协议兼容服务，不依赖 Redis Stack 模块。URL 为空时无需外部服务；启用的 URL 格式非法会启动失败，格式正确但服务离线、认证失败、超时或值被检测为截断/校验失败时回到数据库计算。连续两次后端错误会暂停访问共享缓存五秒，之后再尝试；客户端不进行网络重试。部署 overlay、随机 hex 口令与资源限额见 [deployment.md](deployment.md)。

缓存键隔离当前用户/分享、storage epoch、项目、Run incarnation、实际 data revision、元数据版本、查询与预算。查询仍从 SQL 解析选择和权限，返回前复验授权、身份与 epoch；会话、授权事实与分页快照仍以 SQL 为准。Valkey 只保存可丢弃结果，durable ACK 始终在原始 SQL 事务完成后返回，上传文件仍使用 local/S3。

无论是否命中缓存，每实例最多八个查询响应同时物化/编码；数据库计算另有四个名额，两者排队上限均为 100ms，满时返回 `429 query_busy`。缓存合并最多容纳 64 个不同 key 的计算任务，最后一个等待者取消后会取消该任务。管理员 `GET /api/v1/admin/status` 的 `query_cache` 提供容量、命中、合并、后端错误和超限跳过计数；`shared_cache:true` 表示已配置后端，不表示后端健康。

`MLBOARD_SUMMARY_PROJECTION=off` 仍随摄取原子记录 dirty，但不构建、不启用派生读；`build` 后台构建，未命中缓存后的 summary/曲线仍走原始路径；`on` 才使用恰好覆盖请求 incarnation/R 的派生结果。默认 `off`，与查询缓存开关独立；已有结果缓存仍可命中。当前 cold-step 只覆盖单个已注册 session 的 scalar/step、primary、全部 sessions、latest_logical 和 `min_max/v1`；其他策略或覆盖不足回到受预算原始路径。范围与 worker 资源边界见 [summary-projection.md](summary-projection.md)。

整库恢复/导入需在重新开放流量前轮换 storage epoch，避免复用恢复前的缓存和持久引用；这不是普通重启步骤。使用同版本 `admin rotate-storage-epoch` 或工作区自带的自动轮换恢复工具，完整操作及分享/key 失效影响见 [deployment.md](deployment.md)。

## Bootstrap 配置：仅首次初始化读取

以下变量只在数据库尚无持久设置时读取；随后修改环境变量并重启不会覆盖 Web 管理员已保存的设置。

| 推荐变量 | 兼容旧名称 |
| --- | --- |
| `MLBOARD_BOOTSTRAP_REGISTRATION_ENABLED` | `MLBOARD_REGISTRATION_ENABLED` |
| `MLBOARD_BOOTSTRAP_GITHUB_CLIENT_ID` / `CLIENT_SECRET` | `MLBOARD_GITHUB_CLIENT_ID` / `CLIENT_SECRET` |
| `MLBOARD_BOOTSTRAP_OIDC_CLIENT_ID` / `CLIENT_SECRET` / `ISSUER` | `MLBOARD_OIDC_CLIENT_ID` / `CLIENT_SECRET` / `ISSUER` |

每项优先使用已定义的 `MLBOARD_BOOTSTRAP_*`，即使显式值为空也不会回退到旧名称。注册默认关闭；布尔变量使用严格解析，接受 Go `ParseBool` 支持的 `true/false`、`1/0` 等值，非法非空值在首次初始化时报错。现有实例的注册和 OAuth 配置通过“实例管理 → 实例设置”修改，带 revision 防止覆盖。

OAuth 的 callback 从运行配置 public URL 构造。改变域名、端口或 HTTPS 不改变已经绑定的外部账号；旧版本身份映射的显式迁移和 issuer 隔离见 [admin.md](admin.md)。

部署入口、卷和 APNs secret override 见 [deployment.md](deployment.md)。

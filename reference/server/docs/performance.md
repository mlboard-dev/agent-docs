> 来源：[server/docs/performance.md](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/docs/performance.md) · `73643d8`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 大规模标量数据的性能与边界

SQLite 与 PostgreSQL 使用相同的摄取、revision 和查询语义。2026-10-24 的本机验证分别经 HTTP 写入 `64 runs × 50,000 steps × 2 scalar metrics = 6,400,000` 原始点，每批最多 512 events，核对 durable ACK。当前脚本逐项检查 ACK 中的 session、producer、seq 和重复数；早期 SQLite 摄取阶段检查 accepted 数量和零重复，不能追溯视为已执行后加的逐身份校验。压测脚本位于工作区 `scripts/benchmark-scale.py`；详细主机记录及脱敏原始样本位于工作区 `docs/workhistory/2026-10-24-scale-performance.md` 和相邻 `performance-scale/`。

## 已采用的查询与写入路径

- 摄取在同一事务中批量查重，复用每批 session/descriptor 校验，并按 128 行分块插入。不可变 kind/unit、权限、幂等冲突和 revision 发布规则保持不变；ACK 在持久化事务提交后返回。
- `GET /projects/{id}/runs` 和 `GET /runs/{id}` 支持 `include_summary=false`。显式提供时参数必须恰好出现一次且为 `true` 或 `false`；省略时仍返回 exact summary。元数据模式保留相同 ACL、筛选、排序、分页、计数及版本，返回 `summary:{}`，不读取历史点。导航与选择器可用它先显示数据，需要指标列、排序或 CSV 的页面仍需读取摘要并清楚显示加载状态。
- 查询先以剩余预算加一为上限计算原始源记录数，再加载被接受的点。COUNT 与扫描共用 run revision、kind、metric/context、producer/session 及安全 step 范围谓词。预算数是 canonical 去重和绘图降采样之前的记录数；epoch 等需要 canonical 结果的轴不会被提前错误过滤。
- COUNT 在同一只读事务中检查注册 producer 的 ID 是否全部等于所属 session 的 `primary_producer`。仅当检查成立时，结合数据库的 points → events → producers → sessions 外键链省略 primary JOIN；混合 producer 保留 JOIN，不能用 producer role 代替 ID 判定。SQLite 的计数使用既有 `points_step_range` 覆盖索引，不增加历史索引存储。
- 鉴权仅对确实不存在、过期或 disabled 的凭据返回 401。HTTP 鉴权和 ingest 事务内的用户/成员/API key/session 复验都保留 SQL 或取消上下文的故障为服务错误，不清除仍有效的会话；这不改变 ACL，也不承诺自动重试。
- canonical 去重使用类型化 key→切片索引，并原位压缩和清空尾部；摘要窗口只投影需要的列，保持 session、producer、revision、非有限值与重复 step 的原语义。
- SQLite Compose 使用数据卷中的 `SQLITE_TMPDIR=/data/files/sqlite-tmp`，避免大型并发排序耗尽 64 MiB `/tmp` tmpfs。启动验证目录创建与写入/关闭/删除；未配置时保留 SQLite 默认选择。SQLite 冷摘要最多一个并发，取得名额后重查 exact cache，排队与 SQL 共用原三秒预算；缓存命中不排队，PostgreSQL 不启用该门控。
- Web 的 Dashboard / Run 曲线首屏只读取 metadata 和 series；完整摘要由可见的 runs 来源统计图、面板编辑器和展开的原始汇总按需读取。表格的完整指标排序 / CSV 与公共分享的摘要语义保留。SSE 首次连接和重连会校准元数据，等价版本的图表请求不再被无条件取消；真实更新、reset 和可见性恢复仍完整刷新。当前缓存身份包含不可复用的 run incarnation 及相应 data/run revision，查询结果缓存还隔离 storage epoch 和授权主体。

超限不是截断成功。查询最多选择 50 runs、扫描 1,000,000 原始源点，并受 3 秒超时预算约束；超限返回 `422 budget_exceeded`，超时返回 `422 query_timeout`。四个 query slots 与 100 ms 排队上限耗尽时返回 `429 query_busy`。预算允许的查询仍可能超时，接受的查询也承担 COUNT 的成本。具体请求和错误形状见 [API 契约](api-contract.md)。

SQLite 驱动固定为 `modernc.org/sqlite v1.40.1`，采用 [上游 MR81](https://gitlab.com/cznic/sqlite/-/merge_requests/81) 的取消清理修复：查询已生成 Rows 后才被取消时，先关闭 Rows 再返回取消错误，避免隐藏语句持有读事务和 WAL checkpoint 锁。仅丢弃连接不能释放此类遗留语句的 zombie 锁；单条查询回归中 v1.39.1 关闭连接后 checkpoint 仍 busy，v1.40.1 的语句数归零、回滚与 checkpoint 恢复。该最小修复仍使用 SQLite 3.50.4，并匹配上游要求的 `modernc.org/libc v1.66.10`；不顺带升级其他依赖。驱动真实泄漏修复与应用层提交失败/连接回收防御各有作用；此回归证明故障机制，不单凭相似症状宣布某次远端故障的现场根因，也不代表吞吐或延迟达标。

## 本机样本

主机为 Apple M1 Max、10 核、64 GiB。SQLite 为本机 WAL/FULL；PostgreSQL 17.11 为 OrbStack 内镜像锁固定的独立容器，fsync/synchronous_commit 开启、shared_buffers 128 MB、work_mem 4 MB。未固定两者相同的 CPU/总内存资源，主机亦有共享负载，不能据下表推导引擎排名或生产容量。

| 指标 | SQLite | PostgreSQL |
| --- | ---: | ---: |
| 优化后摄取 c4 分段吞吐，1.2M 点 | 21,237 点/秒 | 43,228 点/秒 |
| 同阶段 ACK p95 | 230.779 ms | 124.750 ms |
| c1 单 run/2 metrics，100k 源点，读取 p95 | 977.861 ms | 729.695 ms |
| c1 20 runs/2 metrics，step 24k–26k，80,040 源点，p95 | 1054.906 ms | 719.400 ms |
| 冷进程 64-run exact-summary 列表 | 3 秒超时 | 3 秒超时 |
| 同进程 64-run metadata 列表 | 1.997 ms | 24.092 ms |
| c1 20 runs/1 metric 全曲线，1M 源点 | 8/8 超时 | 8/8 超时 |

读取每组 8 次，p95 接近该小样本最大值；冷状态只清除应用摘要缓存，OS/数据库缓存保留。并发 8 的重查询通常为 4 次成功、4 次 429；SQLite 的 c4/200k 源点组还发生 8/8 超时。完整报告保留每种状态、比例、实际请求并发峰值、全响应及成功响应延迟，不能只看快速拒绝后的平均延迟。该批 `min_max` 保留极值并限制返回点数，使用需要加载选中源记录的原始路径；后述覆盖 SQL 路径未计入这些测量。

两库均另外检查正负尖峰、首末 step、非有限值断线及相邻点、resume session 对迟到旧 session 的优先级、旧 revision、epoch 范围、精确摘要计数和重试幂等。混合负载仅采样每组 15 秒，不覆盖长期 GC、checkpoint、持续故障或多主机部署。

## amd64 容器样本

2026-10-24 又在 8 vCPU / 约 6 GiB 的 VMware Linux 主机原生构建并测试三种独立 Compose 部署。app 固定 2 CPU、1536 MiB RAM、3072 MiB MemorySwap（含内存的总额）；PG 另占 2 CPU、1024 MiB RAM。两库仍各为 64 runs × 50k steps × 2 metrics，真实 HTTP 写入及 ACK 校验。主机有其他服务，阶段串行；每组读 8 次，不能将结果视为独占主机或生产容量。

| 同数据观察 | SQLite | PostgreSQL |
| --- | ---: | ---: |
| c4 摄取 1.2M 点的吞吐 | 8,192 点/秒 | 25,585 点/秒 |
| c8 摄取 5M 点的吞吐 | 7,101 点/秒 | 15,261 点/秒 |
| c1 单 run/双指标/100k 源点成功 p95，基线→优化 | 2760→2199 ms（7/8→8/8 成功） | 1973→1724 ms（8/8→8/8） |
| 读取阶段非容量错误 500，基线→修复 | 15→0 | 0→0 |

SQLite 基线的 500 来自排序耗尽容器 tmpfs，宿主磁盘仍空闲；专用磁盘目录修复后不再出现。完整 64-run 摘要的 count、finite_count、last、min、max 复核通过；冷进程 8 个并发同 run 摘要请求全部成功，p95 1794 ms。首次逐 run 预热仍有 5/64 超过三秒，保留为失败；c4 全曲线、1M 源点以及高并发重查询仍可能 422/429，不是静默截断。SQLite app RSS 峰值由 583 到 415 MiB，但 Docker working memory 从 714 到 898 MiB，文件缓存也消耗容器内存，不能混用两种口径。PG app Docker working memory 从 811 到 565 MiB。

PG c8 ACK p99 为 7.14 秒、最大 21.28 秒，明显差于 c4，不能只报最大吞吐或无限增并发。完整请求、资源、镜像 ID、源码及方法记录位于工作区 `docs/workhistory/2026-10-24-x86-deployment-performance.md`。

TensorBoard 对照固定 2.20.0 / native data-server 0.7.2，同 6.4M 逻辑点，使用其原生 float32；默认每曲线约 1,000 点预采样，原始文件完整保留。正常前端按 tag 获取日志目录全部 runs，即使 UI 只显示少数 runs。单曲线采样读取很快，但不等于 MLBoard 的完整历史扫描、min/max 极值保留和 revision 语义；本批 train/loss 首次全 run 响应未保留人工加入的正负单点尖峰。浏览器实际返回量、资源预热、首图和本地缩放/范围重查分别列在工作区报告，不以不同工作量计算笼统倍数。

最终 Web 在同一原生容器及系统 Chrome 上复测，PG 的单 run、三 run 全历史、20 run 的 step 0..4999 双图各 n=3 全部成功，共同截图首图上界 p95 为 2.50 / 3.35 / 3.86 秒。首屏不再等待 exact summary，也不因 SSE onopen 取消重发 query；未达到所有页面 1.5 秒的目标。SQLite 单 run 与 20 run 窗口通过，分别为 3.37 / 3.94 秒；三 run 全历史 3/3 未完整成功，6 条 tag query 中 5 条超过三秒预算，只完成一张图的样本不算通过。当前 2 CPU 配额下不适合直接比较这类长历史，不能靠忽略 422 或扩大默认预算描述为性能已解决。

TB 同目录 64 runs 与精确三 run 硬链接子目录的三 run 首图上界分别为 2.90 / 0.65 秒，但后台分别下载 128,000 / 6,000 个默认采样点；MLBoard 对应为 4,776 个保留极值的点并读取完整选中源历史。默认 UI 布局、采样、精度、资源预热和数据库总资源并不相同，以上是具体部署观察，不能作通用倍数排名。

## 复验与后续方向

从工作区根目录运行，所有产物和私有凭据限定在 `outputs/`；先用较小的 `--runs 2 --steps 5000` pilot 估算存储。正式双库 fixture 合计需要约 14 GB 以上数据空间，还要预留 WAL、缓存及至少 8 GiB 空闲。脚本默认不连接日常数据库，PostgreSQL 使用部署镜像锁及独立随机账号/端口；`private.json` 与 `credentials.json` 为 0600，不应提交。

```sh
export MLBOARD_ROOT=/path/to/mlboard
source "$MLBOARD_ROOT/scripts/env.sh"
python3 scripts/benchmark-scale.py create --database sqlite \
  --binary "$MLBOARD_ROOT/outputs/bin/mlboard" \
  --server "$MLBOARD_ROOT/src/server" \
  --runtime "$MLBOARD_ROOT/outputs/performance-scale/repro-sqlite"
python3 scripts/benchmark-scale.py ingest \
  --runtime "$MLBOARD_ROOT/outputs/performance-scale/repro-sqlite" --concurrency 4
python3 scripts/benchmark-scale.py read \
  --runtime "$MLBOARD_ROOT/outputs/performance-scale/repro-sqlite" \
  --samples 8 --concurrency 1 4 8 --cold-restart --warm-summaries --include-limit
python3 scripts/benchmark-scale.py mixed \
  --runtime "$MLBOARD_ROOT/outputs/performance-scale/repro-sqlite" --concurrency 4 --seconds 15
python3 scripts/benchmark-scale.py edges \
  --runtime "$MLBOARD_ROOT/outputs/performance-scale/repro-sqlite"
python3 scripts/benchmark-scale.py stop \
  --runtime "$MLBOARD_ROOT/outputs/performance-scale/repro-sqlite"
```

`stop` 只停止其 manifest 和所有权标记对应的服务/容器，保留数据与报告；摄取可按已确认进度续跑。PostgreSQL 复验改用 `--database postgres` 和另一个 runtime，避免覆盖现有样本。

上述样本未启用下述持久投影和共享查询结果缓存，不能作为新路径的容量证明。新对照需保留峰值、空洞、旧 revision 和 session 语义，并分列构建、命中与回源成本。这轮没有引入独立时序数据库，也没有把应用内摘要缓存视为持久汇总。

## 身份一致性先于复用

Run 元数据包含不可复用的 `run_incarnation`。历史读接口仅接收 typed `RunReadRef`，在自己的只读事务中验证身份及 committed revision，实际 SQL 同时约束 project/incarnation/R，不能用旧 metadata 的 public ID 直接扫描新对象。API 返回前还复核身份、ACL 与分享有效性；summary 缓存也包含 incarnation。SQLite/PG 的回归在鉴权后、history 返回前和暖缓存路径设置 barrier，验证同/跨项目重建不串数据。受限 API key 与公开分享持久绑定具体 incarnation，旧 cursor 不自动跟随替换。

## 可选持久 exact summary

2026-10-25 起可用 [持久投影](summary-projection.md) 分块维护 canonical 与 exact summary checkpoint，原始 ACK 事务只增加 dirty 水位。`--summary-projection off|build|on` 默认 `off`；`build` 只构建不切读，`on` 仅在 incarnation、算法版本和精确 R 覆盖匹配时读取。缺失或滞后仍走原受预算路径，不返回旧摘要冒充当前结果。

cold-step 的首版快路径限定单个已注册 session、scalar/step、primary/all sessions/latest_logical、最多 8 个 metric 项和 `min_max/v1`。在数据库内按实际视口精确分桶、保留原点与 gap 邻接，再取选中事件的元数据；仍有原始预算预检和 canonical 范围扫描。完整 canonical 未追平时，只在同快照有完整 checkpoint C、build 不超过捕获 R 且全部 `(C,R]` 原始尾段不超过 4096 条时尝试精确合并，并重新计算完整视口的 v1；同名候选过多也会保守回源。多 session、缺失完整 C、大尾窗、较旧 R 的尾窗、其他轴或策略回源，不保证所有查询都加速。原始扫描统计复用完整预检，不从部分 source_count 猜测；管理员 `query_reads` 计数可区分 raw/canonical/tail，缓存命中不增。该有界路径经两库小功能 oracle 验证，容量需另行实测；当前未实现多级 tiles 或 delta API。

## 查询结果缓存与观测口径

默认 L1 为 64 MiB、单项 2 MiB、TTL 300 秒，最多 4096 项；可选 Valkey 共享可丢弃的相同版本结果。配额只计算 key/payload，不能作进程 RSS 上限。超过单项大小的合法结果仍返回，但不入 L1/L2；相同版本重复请求与持续变 revision 的请求须分别测量，暖命中不能替代冷首开。具体开关、熔断回源和部署方式见 [configuration.md](configuration.md)、[deployment.md](deployment.md)。

基准至少分列查询缓存关闭、仅 L1、L1+Valkey，并交叉投影 off/build/on、新进程与再次读取、静态与变化 revision。`MLBOARD_QUERY_CACHE_ENABLED=false` 不清除独立的 Run exact-summary 内存缓存；需要冷摘要时重启进程并记录 OS/数据库缓存条件。记录全部成功、422、429、超时、实际并发峰值，以及源点、下载/绘制点、应用 RSS、Docker working memory 和派生存储增量。当前仍受 50 runs、1M 原始源点与三秒查询预算约束。

参考的 [SwanLab Helm chart b93e79b](https://github.com/SwanHubX/charts/tree/b93e79b4343d45902fae68beeee004578b68d876) 将元数据、指标/日志、缓存/会话与对象存储分层，并使用批处理、磁盘缓冲和背压。MLBoard 借鉴这些架构取舍，保留 SQL durable ACK、local/S3 文件和可选 Valkey；不是把 Redis 改名就证明提速，也没有复刻其 ClickHouse/Redis Stack 服务组合。

新大数据对照在固定资源的开发机独立记录，本机仅跑功能、构建与 UI 验证；现有旧报告和小功能测试都不能证明新路径已达到性能目标。

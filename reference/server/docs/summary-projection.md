> 来源：[server/docs/summary-projection.md](https://github.com/mlboard-dev/server/blob/4caeb73c2e0697158c5f376de000da3e6d523d78/docs/summary-projection.md) · `4caeb73`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 持久 exact summary 与 canonical 投影

派生层可从原始 SQL 历史重建，不改变 durable ACK。schema 11/12 增加 `summary_jobs`、`scalar_canonical`、`scalar_summary_blocks`、`run_summary_checkpoints`；原始事件、points、data revision 与 dirty 水位在同一事务提交，全重复重试不推进水位。缺失 dirty 表或写入失败会使整批回滚，不返回成功 ACK。

服务开关 `--summary-projection` / `MLBOARD_SUMMARY_PROJECTION` 接受 `off`（默认）、`build`、`on`。三者都记录 durable dirty；`off` 不建、不启用派生读，`build` 后台构建但未命中缓存后的 exact summary 仍走原始 SQL，`on` 才读取完全覆盖的 checkpoint。`build` 不自动对每份大历史运行昂贵的 raw shadow 对比，应在测试或隔离压测中显式核对。SQLite 一个 worker、PG 两个，批间至少让出 10ms，无任务/竞争时 250ms 后重试；每块最多运行两秒并可取消。数据目录所在文件系统可用空间不足 8 GiB 或不可检查时暂停派生构建，摄取不依赖该检查。PG 数据库若位于别机，还须单独监测其磁盘。

worker 按 incarnation 冻结目标 revision，每块读取最多 128 个事件身份、处理最多 512 个 typed points、重算最多 8 个基础块；canonical 写入采用 128 行 bulk UPSERT。块宽为 256 step；无 Step 的块额外按 session/producer 分区，逻辑身份保留类型化 `(session,producer,seq)`。只处理真正的 session primary producer，不能用 producer role 代替 ID。重复 Step 的 winner 仍按 session ordinal、seq 排序，低 ordinal 的迟到记录只增加源记录计数，不覆盖较新的 winner。

首次回填 `C=0` 仍冻结当时的 requested revision；已有进行中 build 保持原目标与游标。已有完整 C 后，新 build 取 `min(requested, C+8)`，到达完整目标 B 才发布 exact summary 与 `C=materialized=B`，随后继续追 requested。八个 revision 是发布间隔上限，不是八条事件或固定点数；单个大 revision、持续生产快于 worker 或新安装回填仍可能超过 4096 尾窗，不能承诺始终命中快路径。部分 cursor 绝不冒充完整 C，旧 build 也不能中途缩小后给未来 canonical 行贴上旧水位。

被替换的 min/max/last/last-finite 在受影响块内重新计算，保留 NaN/Inf 断点状态。每个 canonical 行和基础块持久保存 canonical 前的 `source_count`；完整 checkpoint 与原始 exact summary 的 count/finite_count/min/max/last/last-finite 相同，不能用绘图采样代替摘要。

job lease token 在写事务内加锁复验。canonical、块统计、游标与覆盖水位一同提交；失效 worker 无权发布。开始修改下一目标的 canonical 时，同事务将 `materialized_revision=-1`，全部追平才置为该 R。完整 canonical 曲线读取必须在同一快照复验 `RunReadRef`、algorithm version 和 `materialized_revision == R`；滞后曲线只有通过下述完整尾窗证明才可读取，不能只看 `checkpoint_revision`。原始 committed revision 可继续增长，当前构建目标不会被中途改变。

checkpoint 按 incarnation/R 不可变保存，保留至少十分钟；旧 R 有 checkpoint 时精确读取，否则回到原始受预算路径。读取前在同一事务验证身份，缺失/损坏或算法版本不匹配的 checkpoint 回源，绝不把当前 canonical 结果用于旧 R。任务启动以元数据水位按最多 128 行分块补齐遗漏 dirty，随后才分块扫描历史，覆盖 schema-only 发布窗口。

启用 `on` 时，cold-step SQL 快路径要求每个 Run 只有一个已注册 session、scalar/step、真实 primary ID、全部 sessions、`latest_logical`、`min_max/v1`，请求最多 8 个 metric 项。完全发布的 `materialized_revision == R` 保留直接读取；多 session、自定义 producer/session、其他轴或原始输出回到既有受预算历史读取。全历史中含无 Step 的 series 回源，明确 step 范围仍按原谓词排除无 Step。

持续训练时可尝试一个严格有界的尾窗。在同一只读快照内验证完整 checkpoint `0 < C < R`、对应发布记录、`C <= build_revision <= R`、`requested_revision >= R`，以及 `materialized_revision` 只能是 `C` 或 `-1`。读取全部 `(C,R]` 选中原始记录，跨该 Run 的全部请求 metrics 合计最多 4096 条，4097 探针即回源。为限制物理扫描，同名但未选中的 context/kind/worker 候选也共用 4096 上限；这可能更早回源。探针按既有 `points_series(run_id,name,revision)` 范围读取，不把 canonical 去重后的行数当作尾窗大小。

证明基于原 winner 规则：当前 canonical 是完整前缀加 worker 已应用子集 `U` 的 ordinal/seq 最大值；`build_revision <= R` 保证 `U` 包含在完整尾段 `T=(C,R]` 中，所以重新取 `winner(canonical ∪ T)` 等于原始历史截至 R 的 winner。不能用 revision 排序，也不能让低 seq 的迟到记录无条件覆盖前缀。SQL 只替换真正胜出的尾段行，再在完整合并视口重算 first/min/max/last、非有限边界和相邻点；不会把已采样的前缀直接追加尾点。分桶使用薄列，选中 Step 后按逻辑 PK 或原始事件 PK 取回引用；尾段只绑定事件身份，最多 8192 个身份参数，避免整行 VALUES 超过 SQLite 参数上限。

预算及 `scanned_points` 仍使用第一遍逐 Run 的完整 `CountPoints` 精确值；部分 canonical 的 `source_count` 含已应用子集，不能与尾段再次相加。canonical 合并计数、applied producer/ordinal、输入点和预算错误均与原始路径保持一致。pinned `at_revision=R` 不必等于第一阶段元数据的最新 revision；只有 store 在同一快照证明完整前缀、`C <= B <= R` 和有界完整尾窗成立时，才允许修补至 R，也可直接读取恰好完全发布于 R 的 canonical。捕获之后的新 ACK 不改变请求 R；若 C 或 build 已超过 R，无法恢复被未来记录覆盖的旧 winner，必须回源，不能过滤未来行后把残留结果称为完整。

无完整 C、缺失发布记录、非法水位、尾窗或候选超量、新 session、全范围尾段中有无 Step 时均回源，不发布部分成功，也不推进持久覆盖水位。超量是内部快路径资格判断，不另添公开预算错误。SQL/取消错误保留为错误；读取仍承担完整原始预算预检和 canonical 视口扫描，不是 O(tail) 查询。worker 长期落后超过 4096 条时仍可能频繁回源，不能据此承诺持续摄取容量。4096 是安全上限，并不保证最大尾窗比原始扫描快或满足三秒；参数边界的 `-race` 正确性测试使用单独的三十秒 store 上下文，不扩大公开 API 预算。

管理员 `GET /api/v1/admin/status` 的 `query_reads` 为进程累计的 `raw_scan`、`canonical_step`、`canonical_tail` 次数，单位是每 Run 通过资格检查后的实际 materialization 路径尝试（包括后续 SQL/超时和预算拒绝；资格探针失败不计入）；缓存命中不增加，进程重启归零。没有主体或 Run 身份字段，公开 frames/applied/diagnostics 不变，可在同 fixture 对照中取计数差证明真实路径。

基础块用于 exact 汇总和覆盖证明，当前没有多级降采样 tiles 或增量 delta API。有界尾窗没有取代完整视口重算；缓存开关与派生层独立，Valkey 不能替代尚未覆盖的计算，见 [configuration.md](configuration.md)。

终态 run 优先追平，等待超过三十秒的任务优先于新终态任务，批间更新调度时间。checkpoint 最多 10,000 个 series、编码最多 16 MiB；超出时任务保留 dirty，原始受预算读取继续作为依据。管理观测可查询 `summary_jobs` 的 requested/checkpoint/materialized revision、build revision、lease 和 last_error；`SummaryProjectionLag` 只计尚未追平的 run 数，不代表剩余源点数。

SQLite 后台写不排队等待 write gate，看到前台写者即让出；PostgreSQL 用 try advisory lock、root/job NOWAIT 和 20ms 锁等待上限。这里的 20ms 是锁等待上限，不是整批 CPU/事务耗时保证。任务可取消，失败只延后重试，不清除 dirty。数据库连接、磁盘、原始数据仍须按实际资源配置；派生行和索引会增加存储。

已领取任务在派生写入前正常让步时，最多尝试四次，间隔 5/10/20ms；继续使用后台 gate/NOWAIT，不进入前台 ACK 队列。原始输入只读取一次，应用前仍在事务内复验身份与 lease token。canonical 写、块汇总及 COMMIT 的错误直接返回，不按“锁忙”重放；即使返回未知 COMMIT 结果而实际已经提交，也不能再次累计 source_count。

正常让步或取消后，以独立 250ms 清理上下文有界尝试归还同 token 的租约；成功后可立即重新领取，不额外加失败冷却。真正源/SQL 故障保留一秒冷却。清理始终服从写者优先；数据库或写者在整个窗口内不可用时，保留过期恢复而不假报归还成功。公开 `ProcessSummaryChunk` 限制每块上下文为两秒，领取的租约至多到该 deadline 加 250ms 归还余量，避免清理失败另留下五秒闲置租约；取消仍有 token fencing，旧任务无权清除新租约。

store 的 `SummaryProjectionStats()` 提供每 DB、进程内原子累计计数：`claim_yields`、`apply_yields`、`lease_releases`、`lease_release_retries`、`lease_release_failures`、`lease_superseded`、`chunks_committed`、`checkpoints_published`。yield/retry 统计尝试；chunk/checkpoint 只在确认 COMMIT 成功后计数，未知结果不假记成功。归还失败与 token 已换手分开，没有 Run ID 或错误正文，不增加高基数日志；计数不替代 SQL 的 requested/checkpoint/cursor/lease 水位和实际延迟采样。

写事务显式持有一个 SQL connection。COMMIT 失败后不自动重试未知的提交结果，并丢弃连接，避免 SQLite 尚未退出的底层事务回池；回调失败先 rollback，rollback 失败也丢弃。提交失败回归用两库的 deferred FK 实际在 COMMIT 时触发错误，分别核对 source/dirty/revision 和派生行/coverage 均未发布、下一次事务与同事件重试可恢复。

Go 确定性回归覆盖两库的有界尾窗/4096与4097原始记录边界/部分构建/未来构建回源/视口 min_max/v1 对照，以及 typed no-Step、primary ID、重复 Step、旧 session 迟到、非有限值、跨 context、多块恢复、source_count、旧 revision 回源、部分覆盖、lease fencing、取消、dirty 事务失败和前台写让出。worker 进度回归还覆盖持有前台 root/job 锁后的同 claim 重试、取消期间归还、旧 token 不清新租约、归还不可用的有界过期恢复、完整 revision 窗口重启，以及真实 COMMIT 已成功但驱动返回未知时不重放 source_count；派生写中的 PG `55P03` 也不能冒充写前让步。两库的 summary/store 与相关完整 query oracle 针对 `-race` 通过，原始日志位于工作区 `outputs/workflow-worker-progress`。大数据吞吐与冷首开容量需在固定资源的远端单独复验，不从这些功能测试推导性能。

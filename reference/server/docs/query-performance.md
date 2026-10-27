> 来源：[server/docs/query-performance.md](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/docs/query-performance.md) · `73643d8`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 查询资源与历史复用

2026-10-26，本轮 B1 / P5 / P6 模块变更记录。实时与事后查询沿用同一授权、incarnation、revision 和 `min_max/v1` 契约；默认 `MLBOARD_SUMMARY_PROJECTION=off`、`MLBOARD_CURVE_TREE=0`、`MLBOARD_QUERY_PROFILE=0`，Valkey 可选。功能开关存在不表示性能目标已达成。

## 大选集与源扫描预算

单查询允许最多1,000个Run、2,000条series、10,000,000条原始源记录；这些也是省略相关预算时的默认值。原先Web显式250,000源记录预算会让几个长Run即触顶，原因是跨所有选中Run/指标的累计候选数，不是只限制返回曲线点数。Store的CountPoints、原始visitor及Step采样入口使用同一10,000,000上限，预检仍只读剩余额度加一。

Web自动图表共享整图10,000个返回点预算，并按所选Run数分配每条采样点（1000 Run时约10点/条，最少8点）。单图请求使用8 MiB字节上限；原始API返回点绝对上限仍250,000，响应全局内存额度、origin并发4、工作集和扫描字节额度不变。扩大选集不是加载1000条完整原始曲线的承诺，其他轴/原始查询仍可能因真实工作集或期限拒绝。

显式预算仍能配置较小额度，已保存方案的显式250,000等值不自动重写。私有Charts的选集、方案保存和重开支持1,000个Run；公开分享的50个Run范围限制、API key资源授权和50个筛选条件限制保持原义。查询上限不授予读取权限。

scalar frame新增可空`elapsed_seconds`列，来自所选原始事件记录，与当前X轴独立；没有记录时为null，不按抽样首点推算。每列仍按实际编码字节计费，分页和可选增量重建保留该列。materialized cache命名空间与snapshot hash使用v4，拒绝混用旧列集的Valkey条目/持久分页快照。

指标目录响应带最终身份复核后的`run_id/project_id/run_incarnation`，新版Web据此省去逐Run的额外元数据复验请求；旧服务仍走复验fallback。周期刷新不会取消尚未完成的一轮大目录读取；权限或reset信号仍可强制重读。目录读取保持最多3个并发，不以1000个同时请求换取短暂首屏。

## B1：在读取和解码前限定工作集

- 公共 `max_scanned_points` 仍计算原始源记录，包括同 step 的输家；`max_bytes` 仍限制完整编码结果，分页不放大总额度。
- 每个 query origin 共用内部累计额度：32 MiB 文本读取、96 MiB 保留工作集估算。SQL 在同一快照、身份、R、predicate、顺序和 LIMIT 下先求字节长度；超限在 payload 进入驱动前返回 `resource_budget_exceeded`。SQLite 使用 BLOB 长度，PG 使用 `octet_length`，NULL 防御性按零长度处理。长度查询会增加 SQL 工作，需单独测量。
- 长度预检先用无排序的 `LIMIT+1` 探测完整性：行数不超过 LIMIT 才证明全集已包含，直接使用顺序无关的总字节；否则丢弃探测总量，执行原 ORDER/LIMIT 的精确前缀预检。额外一条巨大旧 payload 不能让合法短前缀误拒。COUNT、长度、payload 仍不是单次历史扫描，取消不启动后续回退。
- SQL adapter 可同步 `VisitPoints`，在同一 Read 中完成身份校验、整次预算预留和原有有序读取，直接进入 server 分组，避免同时保留整份 `[]store.Point` 与分组副本。兼容 `HistoryStore` 与包装 adapter 继续支持 `ScanPoints`。所有 run 的公共 source-count 预算仍先通过；不逐块释放96 MiB额度、不丢同step输家、不边读边向HTTP输出。callback错误丢弃整次结果并释放行/事务。
- 工作集估算为行数 ×512 + 文本字节 ×2 + 待解码 JSON 字节 ×32；scalar不解码payload，其原文本仍计扫描与保留，native payload继续按32倍。context/unit 按实际 frame 解码再预留。派生节点也按 JSON 解码预算，叶子至多256点、gap目录至多512项，单节点编码至多256 KiB。数组在typed解码前先限制元素数，临时另预留48 KiB；重复字段及array/null/empty保留同一有界backing。估算是保守资源额度，不是实测 RSS。
- 稳定header与可选完整叶分开：每个query origin共用16 MiB且至多16叶的LRU，首次读取即准入，按typed容量和字符串另记96 MiB额度；准入失败跳过，mandatory预算不足先驱逐未pin条目。key含DB/epoch、incarnation、requestedR/baseC、metric/context/cell/算法，每次Read仍证明身份与coverage。完整叶32倍临时解码预留在处理后释放，扫描字节永久累计；header按gap capacity计费。tail生成的新叶和父节点固定保留至该metric reader结束，优先于LRU且不从旧base重读。选点map、bucket、gap按实际typed容量和引用字符串计费；小结果不分配bucket，也不按请求上限预留。每个metric及时清除临时引用再释放，其输出原点仍独立计费。没有减小解码倍率或提高96 MiB额度。
- canonical窄流在SQL侧将状态限制为四个合法enum并累计实际字节；legacy/corrupt宽状态退出到受预算raw路径，不先把大TEXT传入驱动。
- Frame 构建逐行检查实际 JSON 编码贡献，保留转义、Unicode、合法替换字符及非法 UTF-8 与当前编码器一致的长度。历史带空白/重复键的 JSON 按解析后输出计费，不能把原始字符串长度当最小输出大小。
- 响应解码另受进程级256 MiB 加权额度约束（编码字节 ×32），一直保留到 HTTP envelope 结束；100ms 未取得额度返回 `query_busy`。它和既有8个响应/4个origin准入叠加，未放宽公共8 MiB输出限制。
- MCP的最外层queryEnvelope holder把嵌套query租约保留到外层HTTP结束，桥接使用RawMessage避免第二次对象解码和大整数精度损失；不在成功提交写工具后新增容量拒绝，也不表示nonquery结果生成全部受query的256 MiB额度约束。
- 去掉完整结果尾部一次 marshal→decode 往返；非分页结果不额外生成 SQL snapshot body。新 query/snapshot ID、最终授权与固定读取身份复核保留。

分页快照的全局256 MiB准入使用UTF-8字节：SQLite `LENGTH(CAST(result AS BLOB))`，PG `OCTET_LENGTH(result)`，与Go编码后的`len(body)`一致。到期清理、每principal至多64份、全局总字节核对和INSERT仍在同一Atomic事务；PG保留既有critical-metadata advisory lock。显式释放和回滚均不留下容量占用。ASCII、中文、emoji及两个DB实例并发的边界回归使用同一准入函数的小容量，不增加生产配置入口。

## P1：产品默认的标量窄列读取

`projection=off/tree0`下，scalar / Step / primary / all sessions / latest_logical / min_max/v1可使用原始SQL窄流；支持1–8个显式metric/context。它不依赖projection、树、worker或Valkey，也不改变durable ACK。raw transform、其他轴或策略、无Step、未知legacy状态等保留有界回源；显式Step窗口沿用原predicate，可排除无Step记录。

所有Run先通过原公共CountPoints预检。随后每Run在一个身份fenced Read快照内，复用原pointSelection谓词，逐metric核对完整候选数、Step覆盖及窄列字节；只有候选总数与已接受计数相同且未达有界探针上限才选点。R过滤发生在winner选择前，不使用未来canonical，不先对任意事件前缀采样。相同Step按ordinal/seq选winner，相同键保留原source顺序的第一个field。

窄流只传Step、value和有界state。若同快照证明所有候选value均非NULL，winner必无gap，可按已知端点一次流式构造v1桶；否则第一遍确定winner/gap/端点，必要时第二遍构造精确v1桶。临时状态随请求的输出上限增长，完整小结果按实际候选上界预留。每遍永久累计16字节数值列加实际state的逻辑列字节，另持有64 KiB暂存估算和实际typed reducer；它不是socket字节、DB物理I/O或SQL排序/连接总RSS硬限。最终metadata仍按既有行×512、文本×2及frame解码倍率准入，未降低任何系数，也不放宽32/96 MiB额度。

所选`[]store.Point` backing按显式capacity及Step/value holder的typed大小另持租约；每metric临时数组合并时，新/旧/metric数组均先计费，copy后清除旧引用才释放。server分组也在显式capacity增长前另计typed backing，copy期间保留旧buffer额度。P1在坐标/值复制进分组后释放source数组；分组在frame构造完成后清除，输出仍引用的字符串和frame通用预留继续计费。lease归还不退款累计scan/rows，也不声称GC或RSS会立即下降。该公共分组准入同样保留在P1关闭的因果基线中；不能将更严格的拒绝当延迟改善。

最后每128个选中Step回表原始metadata。SQLite使用metric/context/kind/step索引；PG使用有序Step range LATERAL，再在外层精确比对picked Step，避免缺统计时每原点按run主键重扫历史。缺失picked Step不能返回邻点或部分成功。原始输家session/producer/ordinal另作轻投影，`applied`、`diagnostics`、raw-source计数、旧R、峰值/gap及完整frame与原路径一致。`query_reads.raw_scan`仍计算此原始数据materialization，不将其误标为canonical命中。

profile新增`default_step_preflight`、`default_step_narrow_stream`、`default_step_metadata_lookup`、`default_step_sample`及原因`default_step_stream`。前者是SQL证明的行/逻辑列字节，stream记录实际消费的行及同口径列字节估计；父阶段与子阶段不可相加。每metric的SQL字节证明仍重复一部分公共COUNT工作，源身份DISTINCT和metadata长度预检也仍有成本；没有宣称只扫一次历史或跨revision复用稳定块。process/容器RSS、alloc/GC及PG EXPLAIN/统计必须另采，不能用内部reservation下降代替实测物理内存/I/O改善。

功能回归覆盖两库v1独立oracle、gap/plateau、0–MaxInt64跨度、多session、低seq/迟到输家、field tie、旧R、并发未来写入、删除重建、字节拒绝与取消恢复。小fixture EXPLAIN仅证明访问计划，性能验收仍须开发机同fixture、固定资源、产品默认off短组及ACK门；本节不声明API目标达成。

## P5：可关闭的阶段诊断

`MLBOARD_QUERY_PROFILE=1` 在服务日志输出 request_id、阶段耗时/行数/字节及低基数原因计数，不输出查询内容、payload 或凭据。阶段覆盖准入、授权解析、cache/origin等待、DB连接取得、source count、tail/历史读取、节点解码、metadata及其字节预检、frame、材料化编码/解码和响应写出；另记累计scan、peak retained估算和leaf LRU命中。

另记录分组、逻辑去重、排序和minmax。Visitor的 `raw_payload_read` 包含同步group callback，`raw_group_build`只累计callback内时间；旧ScanPoints的raw阶段没有这个子阶段，不能直接将前后raw阶段差值当SQL节省。profile关闭时不逐点计时或加trace锁。最终大小检查的取消统一为 `query_timeout`，避免预算边缘被误报为500。

父阶段包含子阶段，不能相加得总耗时；`budget_source_records` 是公共预算语义值，不是实际扫描行数。COUNT 与采样目前分别执行 coverage/tail 证明，不能宣称只读一次。coalesced 请求共享 origin：leader 已结束时打印的快照可能尚未包含 producer 的后续阶段，不能拿它代替完整 producer CPU profile。profile 开关本身的开销与正式延迟分组测量。

既有canonical选点也分开记录`sample_byte_preflight`与`canonical_metadata_read`。PG新run缺统计时，等值LATERAL可能选blocks前缀索引，逐点扫描整run；采用真正的`step_key>=picked`有序主键seek，LIMIT外再精确校验step/run_id。默认keys仍在seek内部，缺step或不同key不返回相邻值，字节预检与实际读取仍执行同一statement/args/快照。SQLite沿用原查询。

## P6：SQL 中的版本化曲线节点

schema14 新增 `curve_nodes`、`curve_coverage`、`curve_backfills` 与版本/GC索引，保持旧11/12/13迁移来源。share13以独立版本存在性判断，避免更高版本遮蔽尚缺列的旧库。迁移不改写源事件。

第一条支持路径为 scalar / Step / primary producer / 所有session且实际唯一session，至多8个显式指标。范围树保存 first/last/min/max 原点引用、canonical/finite/source_count、gap；按实际视口端点和 gap 数复现 v1 桶规则，边界下钻。缺证明、多session/不支持策略、无step、过大尾窗等继续有界原始路径；不能用 canonical 点数代替源预算。

- 已完成训练首次打开：worker生成的完整 coverage 可免去整段 canonical 窄流和原始 COUNT；选中点元数据按不可变事件键批量回表。SQLite显式使用既有事件主键；PG用parameterized LATERAL加LIMIT选最小field_index，再在外层检验R，避免planner先扫描整run再hash join。跨query/Valkey块缓存尚未实施。
- 实时：只使用 `C≤R` 的完整版本，检查 `(C,R]` 同名全部候选，合计至多4096条；未选择context/kind/producer也计入证明工作。尾窗按原 ordinal/seq/field winner 合并，合法低seq输家照样增加 source_count。迟到旧step会替换受影响叶及父节点，不假设append。
- 旧R：版本适用区间与原始尾窗固定R，未来 canonical winner不能污染过去。删除重建仍校验 incarnation；授权仍在查询入口和返回前执行，节点不构成独立访问入口。
- publication与summary完整 checkpoint 在受 fencing 的同一事务完成；总 canonical/source_count 与summary块校验后才发布coverage。flag首次启用的旧完整projection由可续传backfill每事务至多4个leaf block补齐，移动R会重启cursor；未齐全不能发布部分树。
- 派生版本至少保留10分钟，GC只删除过期coverage和被替代节点，不删除源记录。过旧R缺证明时回源或明确预算失败；持久分页结果不依赖旧节点持续存活。

worker异步构建不改变durable ACK定义，但会增加SQL写入、索引、WAL/SQLite写者竞争和磁盘占用。须连同ACK p95/p99、workerCPU/lag和净派生字节一起报告，不以读取收益掩盖写放大。

## 验证与回退

本地SQLite定向race、远端同宿主PG定向race覆盖v1 oracle、稀疏步/gap、同step覆盖与低seq输家、旧R/未来build、范围、backfill/GC、incarnation删除、0/11/12/13→14、资源拒绝恢复。2048→8192源记录、每曲线32点的小fixture中输出均31点、tree读均44节点，叶点解码878→0；这是低分辨率工作量证明，不能外推500/3000点、高并发或整条API收益。

同一Mac50k×2metric/500点门先真实触发96 MiB拒绝，修复临时节点保留后通过，随后暴露metadata回表47.39秒。EXPLAIN确认SQLite选择`points_series`范围扫描；对不可变事件键限定既有主键索引后，同fixture总store查询190.4ms、metadata21.5ms，扫描12.95MB、返回994点，实际叶点解码159904（含预读与边界重读）。这些是单次store fixture证据，前后的失败与慢日志保留，不能当远端API分位数或高分辨率已经不再随历史增长的普遍证明。

随后origin内叶复用在同形状store门中减少为528个node、100000叶点解码、扫描8.14MB、peak retained估算11.09MB，单次查询169ms；密集500点及413步小窗均与原v1逐点相等。边界叶首次解码仍可能随历史长度增长，children跨Read仍可能重读，不能称所有节点仅解一次。PG b89远端短组暴露实时全部timeout；补诊断停止writer后仍timeout，metadata占75%–88%，pool仅几十微秒。128个事件回表的实际EXPLAIN显示旧SQL扫描88784行并执行等量MIN探测，LATERAL变为128次主键探测。顺序plan对照受cache冷热影响，只用于确认查询形状，新的完整API收益须另测。

1000项合成对象微基准中，旧marshal+decode约2.35–3.25ms、1.48–1.50MB；size walker约0.589–0.611ms、136KB。它只证明这一步的分配减少，不是API加速倍数。

原始成功与失败日志均保留在根仓库 `outputs/next-optimization-implementation/performance`。PG经SSH tunnel的整套测试曾因内部2秒chunk预算失败，同宿主定向race通过；不能删除失败或把LAN组改写为成功。正式同负载baseline/candidate和高分辨率预算、长期、故障、两实例验收另以完整报告为准。

基准命名：`projection=on/tree0`是既有投影路径，**不是产品默认值**；产品默认是`projection=off`。两者需要独立基线和验收。6cd8短PG主组在on/tree0下读196/196成功，但p95比8be退化约49%；on/tree1读372/372成功，p95为541ms，仍未达到300ms目标且静态多run更慢。后续额外诊断继续增长到约69k步时rawfallback触发96 MiB工作集守卫，尽管仍低于用户的源点预算；该内部容量失败保留，不能宣称所有小于1M源点的查询均能成功。长时组必须等最终短组和ACK门通过后才能扩展。

acd8的product-off静态四并发出现14次timeout与2次500，作为red保留并停止该候选扩量。独立6请求profile中raw payload约占origin的56%–73%，原长度预检约15%–20%，连接等待很小；完整源50k×2的长度SUM计划实际external merge约16 MiB。无排序完整性探测的交替EXPLAIN消除了该sort、行数/字节完全相同；这是SQL形状证据，visitor与新完整API性能仍须下一内容快照重测，不能把错误映射改422视为退化已修。

回退：先置 `MLBOARD_CURVE_TREE=0`，必要时恢复 `MLBOARD_SUMMARY_PROJECTION=off`；profile可独立关闭。保留源数据与schema14表，不执行降级删表。任何oracle/身份错误立即停止该路径；相同负载新增5xx、OOM、ACK p95/p99退化超过20%或8GiB磁盘保留线不足则停止扩量并回退。API p95≤300ms、冷≤500ms、暖≤100ms、首图≤1.5s、ACK到画面≤2s仍为目标，当前笔记不宣称达成。

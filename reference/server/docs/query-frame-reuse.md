> 来源：[server/docs/query-frame-reuse.md](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/docs/query-frame-reuse.md) · `73643d8`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 可选曲线帧增量传输

`MLBOARD_QUERY_DELTAS=0`（默认）保持普通查询响应。设为 `1` 或使用 `--query-deltas` 后，私有 scalar 查询的完整单页结果可附带 `mlboard.frame-reuse/v1`。公开分享、结构化数据、分页继续使用完整响应。此功能只减少传输，不替代数据库读取、原始点预算、最终鉴权或曲线范围树。

客户端先发送原来的 `mlboard.query/v1` 请求。服务器可返回完整 `frames` 和：

```json
{"reuse":{"schema_version":"mlboard.frame-reuse/v1","mode":"reset","token":"base_...","row_ids":{"frm_...":["opaque-row-id"]}}}
```

客户端确认支持这个版本后，下一次相同语义查询可加：

```json
{"reuse":{"schema_version":"mlboard.frame-reuse/v1","base_token":"base_..."}}
```

服务端每次仍计算并授权新的完整结果。只有补丁更小时才返回 `mode:"delta"`：`frames:[]`，`reuse` 含 `base_token`、新 `token` 和 `patches`。每个 patch 包含完整 frame 头、固定顺序的列名 `columns`、完整行顺序 `order`、删除 ID `remove`、以及 `{id,values}` 形式的 `upsert`。新 query ID、ETag、consistency、诊断和页信息仍在外层，不能沿用旧水位。

行 ID 来自原始事件身份与实际 X 的哈希。迟到记录可以替换过去的 winner；null/NaN/Inf 状态和每点 event_ref 均原样保留。全历史范围增长会改变 min/max 分桶，补丁可能不合算，这时返回完整 reset。没有“只把新点接到旧采样后面”的假设。

单次reset/delta最多2,000个scalar frame、合计10,000行，与扩大后的私有选集一致；完整重建结果仍受8 MiB与浏览器节点预算约束。nullable `elapsed_seconds` 与其他原始列一起传输，不从旧frame或抽样坐标推导。服务端materialized cache/snapshot namespace v4隔离旧列集；frame-reuse协议本身仍为v1。缓存保留字节限不因此放大，较大合法完整结果可显示而不进入可选复用缓存。

基线身份包含主体、存储 epoch、项目、Run incarnation 集合以及完整查询语义（轴、范围、选择、策略、预算等）。它不跨账号共享。权限撤销、删除重建或预算变化仍由普通查询路径先验证。固定旧 revision 和最新读取不会混用基线。

服务端缓存仅存编码帧：2 MiB/项、64 项、总 16 MiB、2 分钟 TTL/LRU；额外解码也经过响应内存准入。浏览器为 2 MiB/项、32 项、总 16 MiB、2 分钟，退出账号清空。限制是编码保留量，不是进程 RSS 承诺。多实例可随时缺少基线，直接 reset；不依赖粘性会话，不把帧放入 Valkey。

浏览器校验列长度、行身份、删除/替换和新顺序，并按**重建后的完整结果**计预算。未知/过期基线或服务器回滚时，最多重试一次不带 hint 的普通查询。鉴权失败、429、取消不会作为协议故障重放。旧客户端不发送新 hint，因此始终得到完整 frames；旧 `reuse.result_etag` 输入仍保留兼容。

启用 profile 时，`frame_reset`、`frame_delta`、`frame_wire_saved_bytes` 报告协议选择和相对 reset 的编码字节差，不能据此声称 SQL 工作量下降。完整 schema 位于 `internal/server/schemas/query.schema.json` 和 `query-response.schema.json`。

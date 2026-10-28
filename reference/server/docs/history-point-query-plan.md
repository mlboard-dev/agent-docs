> 来源：[server/docs/history-point-query-plan.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/docs/history-point-query-plan.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# SQLite 有界 point count 的查询计划

2026-10-25，调查基线 server `6bfc074`。驱动为项目实际使用的 `modernc.org/sqlite v1.39.1`，`sqlite_version()` 为 `3.50.4`。隔离 fixture 共 3,040 个 point，启用外键、WAL/FULL；仅做 SQL 计划和结果等价检查，没有本机大数据或时延基准。

## 证据

原 `CountPoints` 强制使用 `(run_id,name,context,kind,step,revision)` 索引，但多个 metric/context 的 OR 使未执行 `ANALYZE` 的计划只约束 `run_id`：

```text
SEARCH p USING COVERING INDEX points_step_range (run_id=?)
CORRELATED SCALAR SUBQUERY 1
SEARCH r USING INDEX runs_incarnation (run_incarnation=?)
```

此 fixture 的目标 Run 有 2,560 个索引项，窗口只匹配 16 个 point。VDBE 原计划的 `SeekGE/IdxGT` 只使用 1 个索引键，再通过循环内的 metric/context/step 判断过滤。身份子程序没有 `Once`，但出现在上述过滤之后；因此不是每个被遍历的索引项都重新查 Run。不能仅凭此小样本推算远端耗时。

候选在同一只读事务中验证 RunReadRef，并保留 SQL 的 project/incarnation 谓词：

| 候选 | 未 ANALYZE 的 Count | ANALYZE 后的 Count | Scan 的限制 |
| --- | --- | --- | --- |
| 原 OR + 相关 identity | 仅 run_id seek | 此 fixture 改为 multi-index OR 的完整范围 seek | 两种统计状态均使用 multi-index OR 范围 seek |
| OR + 常量 identity | 仍仅 run_id seek | 同上 | 只消除 identity 的相关执行 |
| tuple-IN + 强制索引 | 完整 metric/context/kind/step seek | 同左 | Scan 没有索引提示，tuple-IN 在 ANALYZE 后选择了 `SCAN p`，不可直接共用 |
| 去重 metric 后 UNION ALL | 每支完整范围 seek | 同左 | 仍需外层全局排序和单个全局 LIMIT，改动更大 |

tuple-IN 的 Count 计划为：

```text
SEARCH p USING COVERING INDEX points_step_range (run_id=? AND name=? AND context=? AND kind=? AND step>? AND step<?)
SCALAR SUBQUERY 1
SEARCH r USING INDEX runs_incarnation (run_incarnation=?)
```

VDBE 使用 5 键范围 seek。`r.id=?` 绑定同一 `ref.RunID` 后，identity 子程序有 `Once`。原始 SQL、参数、完整 EQP/VDBE 及 7 组候选结果对照保存在根工作区忽略的 `outputs/sqlite-point-plan/{main.go,report.json,small.sqlite3}`；其中没有业务凭证，也没有改动正式基准 fixture。

## 最小实现与回归

仅 SQLite Count 使用 `(p.name,p.context) IN (VALUES (?,?),...)`，同时保留 `INDEXED BY points_step_range`。IN 是集合成员测试，重复 selector 不会重复计数。Scan 和 PostgreSQL 保留 OR 及原有索引策略；Count/Scan 的 source、revision、primary/session/producer/step 谓词和单个外层 LIMIT 不变。

Events、Series、原始 Summary、Count/Scan 及 summary worker 的单 Run point 查询，将 identity EXISTS 的相关 Run ID 改为同一个已绑定 Run ID。事务内 `ValidateRunReadRef` 和 SQL 的 project/incarnation 检查均保留；worker 的 chunk、lease、游标和覆盖策略不变。

[查询计划与语义回归](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/internal/store/history_plan_test.go) 在真实 SQLite 上同时断言有/无 ANALYZE 的完整范围 seek、常量 identity；两库覆盖重复 selector、200 个 selector、全局 LIMIT、成对 context、primary、session/producer、无 Step、旧 revision 和非法参数。现有 ABA/旧 cursor、原始 summary 与持久投影回归继续使用同一测试环境。

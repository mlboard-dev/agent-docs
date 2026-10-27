# 数据查询

REST 路径均以 `/api/v1` 开头。先发现项目/Run，再读 series 目录，最后构造有预算的查询。

1. `GET /projects` 返回当前主体有权访问的项目。
2. `GET /projects/{id}/runs?include_summary=false&limit=100` 用于元数据和选集；持续读取 next_cursor 才是完整列表。精确指标分析再请求默认摘要或 `GET /runs/{id}`。
3. `GET /runs/{id}/series` 获取名称、完整 context、kind 和坐标支持。保留响应的 project_id、run_id、run_incarnation；不要仅按显示名去重。
4. `POST /projects/{id}/query`，参照 [查询模板](../examples/query.json) 与 [生产 schema](../schemas/query.schema.json)。固定实验选择可提供 run_incarnations 防止同ID重建后读到其他实验。
5. 读 frames 的 fields/columns、applied、diagnostics 与 page.next_cursor。分页必须保持同一查询与快照；401/403/404重新处理授权，410重新开始读取，不能把页拼到另一个快照。

`runs.run_ids: []` 表示显式空集合，不能当作全部实验。省略 selector 条件与空数组含义不同。不要把本地筛选结果无意扩大成全项目查询。

## X 轴与数值

Step / processed_samples 使用十进制整数字符串；epoch、训练/会话耗时是数值；wall_time 使用原始RFC3339时间。`columns.x` 对应所选轴，不能无条件命名为Step。Relative展示可使用独立的 elapsed_seconds 列，并保留null；当前Step降采样存在[已记录耗时仍可能缺失的限制](../KNOWN_ISSUES.md)，不能据此认定训练没有记录。value_state的NaN/Inf和缺口不能变成0。config精确数字另见 [字段与连续性](../reference/server/docs/frontend-analysis-continuity.md)。

## 当前基线预算

私有查询最高1,000 Run、2,000 series、10,000,000源记录；源记录跨选集/指标累计，包含被逻辑去重覆盖的记录。输出绝对上限250,000点/8MiB。Web自动图表另用约10,000点共享预算；扩大选集不表示整段原始历史都下发。公开分享的50 Run边界独立。

读取默认60秒，实例可配置1–600秒；显式query timeout可缩短但不能超过实例上限。旧方案里的显式短预算保留。执行前以 capabilities 和响应 applied 为准，遇预算错误调整选集、范围、采样或明确预算；不要只增加网络超时。

[API 契约](../reference/server/docs/api-contract.md) · [查询性能与边界](../reference/server/docs/query-performance.md) · [读取期限](../reference/server/docs/configuration.md) · [结构化图表](../reference/server/docs/charts.md)

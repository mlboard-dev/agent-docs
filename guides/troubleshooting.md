# 排障与边界

| 现象 | 先核对 |
|---|---|
| 项目/组织看不到，404 | 账号是否仍是组织及项目成员；ID是否真实；key范围是否覆盖。管理员不自动跨组织。 |
| 403 | scope、项目/方案权限；cookie写入还需正确Origin/CSRF。不要反复猜ID。 |
| 412 | 版本已改变；重新读revision/etag并重建preview。 |
| 410或快照失效 | 从第一页重新查询，不能混接不同snapshot。 |
| budget_exceeded | 看details.limit，减少Run/series/窗口或调整显式预算。采样不自动免除源扫描额度。 |
| query_timeout | 看实例读取期限及query显式timeout；网络超时应允许服务端完成并写出。 |
| query_busy / 429 | 有界退避并限制并发，不同时重试所有面板。 |
| 图表有数据但汇总为空 | 元数据模式summary:{}不表示没有指标；需要精确摘要时另读。 |
| 无Step的文本/表格/媒体不显示 | 检查记录支持的轴，尝试wall_time；不能捏造Step。 |
| HTML空白 | 先保存方案、核对query_refs/fields及html scopes；原HTML文件没有宿主数据桥。 |
| SDK显示accepted但服务端没有数据 | accepted仅入队；检查sync=background、finish(remote)、key、网络和spool状态。 |

当前API Query返回complete/固定快照及预算诊断；不要将异常降级为空数组或声称是完整结果。精确最后值/最值从正式摘要读取，采样展示点不能代替全量统计。指标“越大越好/越小越好”需要任务明确方向。

模块中的历史性能数字各有版本、数据形状和冷热条件。需要压测时另行指定负载、数据库、资源限制与完成标准，不把本仓库的文档验证当作吞吐测试。

[查询边界](querying.md) · [资源期限](../reference/server/docs/request-boundaries.md) · [配置](../reference/server/docs/configuration.md) · [SDK恢复](../reference/py-client/docs/storage-and-recovery.md)

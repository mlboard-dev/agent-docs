# 编辑分析方案

Agent 的持久化对象是 DashboardSpec。普通阅读时的临时调整不自动成为新修订；修改主站导航/整站页面属于产品开发，不属于 Dashboard API。

从零创建使用 REST `POST /api/v1/projects/{project_id}/dashboards`，body为 `{title, visibility, spec}`。visibility显式选 personal 或 project；旧请求缺省project。服务端分配dashboard_id并覆盖spec中的project/dashboard ID。MCP目前没有创建方案工具。

修改已有方案：

1. GET `/api/v1/dashboards/{id}`，保留完整spec、字符串revision和etag。确认can_edit及个人/共享范围。
2. 构造 `mlboard.dashboard-change/v1`，使用唯一client_request_id、读取到的base_revision与真实panel/query ID。[变更模板](../examples/change.json) 仅演示格式。
3. POST `/api/v1/dashboards/{id}/preview`。检查返回的spec/diff及查询、选集、布局是否保留了无关内容。
4. 在用户已有授权范围内，POST `/api/v1/dashboards/{id}/apply`，body为 `{preview_id, client_request_id}`，If-Match为步骤1的完整etag。
5. 再次读取确认修订、返回页面链接。没有实际执行apply时明确报告只有预览。

preview10分钟有效并绑定当前用户；412重新读取和生成预览，不能只改版本号覆盖。幂等重试使用同一preview及request ID；不要将ID挪用于另一预览。历史与restore见正式指南。

项目共享方案需要项目编辑权限；viewer可以在相应scope下创建/编辑自己的个人方案。改布局用dashboards:layout，改内容/查询/选集用dashboards:write；发布HTML另有权限。

布局为12列网格，最终卡片不能重叠；多次移动可放在同一变更中验证终态。共享query的修改会影响所有引用面板；只改一图的轴时复制query并更新query_refs。Run/配置/表格字段建议使用FieldRef，参见 [字段身份](../reference/server/docs/frontend-analysis-continuity.md)。

[完整 Agent 编辑说明](../reference/server/docs/agent-dashboards.md) · [Dashboard schema](../schemas/dashboard.schema.json) · [变更 schema](../schemas/agent-change.schema.json) · [图表类型](../reference/server/docs/charts.md)

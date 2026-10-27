# 组织、项目与 Agent 权限

普通有效登录账号可以创建组织，创建后自动成为owner。组织列表只显示真实成员关系，实例管理员也须先由组织管理者加入已有组织，不能凭全局角色直接浏览或给自己加入。

组织管理与实验数据访问分开：组织owner/admin或已入组的实例管理员可管理成员及项目权限目录；读实验仍要求明确项目成员角色。移出组织会撤销该组织项目成员、项目key和订阅，同一旧会话不保留访问权。

Agent通常使用项目key，key scopes与账号当前组织/项目权限取交集。API key不能创建/管理组织；项目创建需要global key + projects:write +组织内创建权限，普通训练建议使用预建项目。

| 任务 | 典型 scope |
|---|---|
| 读元数据/摘要 | runs:read |
| 查询指标 | data:read（实际流程通常同时需要runs:read） |
| 写Run/上传事件 | runs:write、data:write |
| 读取分析方案 | dashboards:read |
| 只改布局/分区 | dashboards:layout |
| 改面板内容/查询/选集 | dashboards:write |
| 发布HTML/修改绑定能力 | 额外html:publish / html:bind_data |

个人方案由owner访问和编辑，仍要求项目读取权限；共享方案要求相应项目编辑权限。run限制key不能组合全项目方案/成员/分享管理权限。权限不足要返回给用户明确的缺失条件，不擅自扩大key权限或借用管理员身份。

[组织说明](../reference/server/docs/organizations.md) · [API身份与权限](../reference/server/docs/api-contract.md) · [方案权限](../reference/server/docs/agent-dashboards.md)

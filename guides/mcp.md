# MCP 接入

MLBoard提供HTTP JSON-RPC端点 `/mcp`，也接受 `/api/v1/mcp`。使用与REST相同的Bearer API key。客户端必须支持HTTP传输并能安全配置Authorization header；本仓库不提供stdio启动器或自动安装客户端配置。

先initialize（当前支持2025-03-26/2025-06-18协议版本），再tools/list，按返回inputSchema调用tools/call。当前advertise的能力是tools；没有resources/prompts目录。示例见 [initialize](../examples/mcp-initialize.json)、[tools/list](../examples/mcp-list-tools.json)、[tools/call](../examples/mcp-tool-call.json)。

| 工具 | 用途 |
|---|---|
| mlboard.list_projects | 列出有权限的项目 |
| mlboard.list_runs | 读取指定项目实验列表 |
| mlboard.get_run | 读取单Run及规范摘要 |
| mlboard.query | 执行有预算的数据查询 |
| mlboard.get_dashboard | 读取方案与revision/etag |
| mlboard.validate_dashboard | 校验完整spec |
| mlboard.preview_dashboard | 预览命名操作 |
| mlboard.apply_dashboard | 在版本条件下应用预览 |
| mlboard.dashboard_history | 读取版本历史 |
| mlboard.capabilities | 查询实际能力与预算 |

MCP覆盖部分REST能力，不包含创建组织、创建方案、上传训练事件或artifact。当前list_runs工具参数只包含project_id；需要include_summary=false、筛选或cursor分页时使用REST，不把一次工具返回当作完整项目列表。

查询先通过REST registry/schemas确认类型和结构，再调用query。写入流程、权限和版本冲突与REST完全相同；apply的if_match参数传get_dashboard返回的完整etag。工具返回的isError、structuredContent.error和JSON-RPC error都要检查，HTTP 200不等于工具成功。

只给训练权限的key不能编辑方案。不要把实例管理员会话当成项目key发给Agent；参见 [权限](permissions.md)。

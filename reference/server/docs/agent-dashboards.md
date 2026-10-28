> 来源：[server/docs/agent-dashboards.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/docs/agent-dashboards.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# Agent 编辑分析视图

Agent 通过 HTTP 或 MCP 编辑持久化的 DashboardSpec，无需操作浏览器。图表示例页面也是普通 Dashboard。页面右上角“Agent 操作”使用同一套命名操作、预览和应用接口，并不内置或调用大模型。

## 凭据与权限

在“API 密钥”创建绑定目标项目的 key，由环境变量传给 agent。编辑项目共享方案须有项目编辑权限；项目 viewer 可在相应 scope 下创建和编辑自己的个人方案。scope 与实时项目权限、方案可见性和所有权取交集。

| 工作 | 所需 scope |
| --- | --- |
| 读取视图 | `dashboards:read` |
| 移动/调整面板尺寸、整理分区、修改视图标题和分组 | `dashboards:layout` |
| 增删面板、修改面板标题/图表选项、查询和 run 选择 | `dashboards:write` |
| 查看 runs / 读取指标数据 | `runs:read` / `data:read` |
| 发布 HTML / 更改 HTML 数据绑定 | 额外 `html:publish` / `html:bind_data` |

只整理布局可用 `dashboards:read` + `dashboards:layout`。更改图表数据或类型应使用 `dashboards:write`；layout key 不会顺便获得查询/HTML 编辑能力。Run 限制 key 不支持全项目 Dashboard 管理。

## HTTP 工作流

所有下列路径以 `/api/v1` 开头，使用 `Authorization: Bearer <key>`。

1. `GET /capabilities`、`GET /registry`、`GET /schemas` 获取实际面板类型、选项、查询语义和限制。
2. `GET /dashboards/{id}` 读取 `spec`、字符串 `revision` 和完整 `etag`，不要凭页面名称猜 panel/query ID。
3. 构造 `mlboard.dashboard-change/v1` 并 `POST /dashboards/{id}/preview`。返回 `preview_id`、`spec`、`diff` 和 `expires_at`；这一步不改变已发布页面。
4. 检查预览结果后 `POST /dashboards/{id}/apply`，请求体为 `{preview_id, client_request_id}`，`If-Match` 使用第 2 步的 `etag`。
5. 再次 GET 确认新修订。视图历史可通过 `/history` 读取；`POST /restore` 携带 `{revision}` 和当前 `If-Match` 恢复为新修订。

预览有效期为 10 分钟并绑定当前用户。412 表示基础修订已变化，应重新读取、重新生成预览；不能简单把旧变更换成新版本号强行覆盖。相同 preview 和 `client_request_id` 可幂等重试 apply；同一 request ID 不可改用于另一预览。

下面示例使用 Python 标准库，将第一个面板移到现有布局末尾，并扩到 12 列。先仅生成预览，末尾给出应用调用。环境变量 `MLBOARD_SERVER` 是实例地址，`MLBOARD_DASHBOARD_ID` 是页面 URL 中的 `dsh_...`，`MLBOARD_API_KEY` 是上述项目 key。

```python
import http.client
import json
import os
import uuid
from urllib.parse import urlsplit

origin = urlsplit(os.environ["MLBOARD_SERVER"].rstrip("/"))
dashboard_id = os.environ["MLBOARD_DASHBOARD_ID"]
key = os.environ["MLBOARD_API_KEY"]

def request(method, path, body=None, etag=None):
    connection = (
        http.client.HTTPSConnection if origin.scheme == "https"
        else http.client.HTTPConnection
    )(origin.netloc, timeout=15)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if etag:
        headers["If-Match"] = etag
    try:
        connection.request(method, origin.path + "/api/v1" + path,
                           None if body is None else json.dumps(body), headers)
        response = connection.getresponse()
        data = json.loads(response.read())
        if response.status >= 300:  # 不跟随重定向发送凭据
            raise RuntimeError(response.status, data)
        return data
    finally:
        connection.close()

dashboard = request("GET", f"/dashboards/{dashboard_id}")
items = dashboard["spec"]["layout"]["items"]
first = items[0]  # 实际任务应按读取到的面板 ID 选择目标
request_id = "agent_" + uuid.uuid4().hex
change = {
    "schema_version": "mlboard.dashboard-change/v1",
    "client_request_id": request_id,
    "base_revision": dashboard["revision"],
    "reason": "将目标图表移到末尾并加宽",
    "operations": [
        {"op": "move_panel", "panel_id": first["panel_id"], "x": 0,
         "y": max(item["y"] + item["h"] for item in items)},
        {"op": "resize_panel", "panel_id": first["panel_id"], "w": 12, "h": 16},
    ],
}
preview = request("POST", f"/dashboards/{dashboard_id}/preview", change)
print(json.dumps(preview, ensure_ascii=False, indent=2))

# 检查上述 spec/diff 后，在同一进程中调用：
# result = request("POST", f"/dashboards/{dashboard_id}/apply", {
#     "preview_id": preview["preview_id"], "client_request_id": request_id,
# }, etag=dashboard["etag"])
```

`x/y/w/h` 是 12 列网格坐标和尺寸，必须完整且不重叠。移动、扩宽和为邻图让位可放在一个变更中，校验的是整组操作后的最终布局。例子移动到所有现有格子之后，因此不会覆盖邻图。

其他常用操作包括 `add_panel`、`remove_panel`、`update_panel`、`upsert_query`、`set_selection`、`upsert_section`、`set_section_order`、`set_panel_section` 和 `set_view`。查询与坐标必须符合实际 registry/schema；修改共享 query 会影响所有引用它的面板，单图改轴应复制查询并更新该图的 `query_refs`。

## MCP

HTTP JSON-RPC 端点是 **`/mcp`**。携带同一个 Bearer key，支持 `initialize`、`tools/list`、`tools/call`。主要工具映射如下：

| 工具 | 用途 |
| --- | --- |
| `mlboard.capabilities` | 查询可用能力和预算 |
| `mlboard.get_dashboard` | 读取 spec、revision、etag |
| `mlboard.query` | 在项目权限下读实验数据 |
| `mlboard.validate_dashboard` | 校验完整 spec |
| `mlboard.preview_dashboard` | 提交上述 change，取得预览 |
| `mlboard.apply_dashboard` | 使用 preview_id、client_request_id、if_match 发布 |
| `mlboard.dashboard_history` | 读取历史 |

例如 `tools/call` 的 `params` 为 `{"name":"mlboard.preview_dashboard","arguments":{"dashboard_id":"dsh_...","change":{...}}}`。apply 的 `if_match` 传 get_dashboard 返回的完整 etag。MCP 只是同一权限和版本校验的适配层，没有额外管理权限。

## 页面效果与边界

- 保存布局是共享 Dashboard 数据；本次新增的“放大图表”是临时阅读状态，不发布修订。
- 浏览器开启“自动布局”时，卡片宽度/换行由当前显示设置决定；查看 Agent 保存的精确网格位置时关闭自动布局。按指标分组也会覆盖手工分区的展示方式。
- 全局显示精度、临时轴选择、每图平滑等浏览器偏好不等于 Dashboard 修改。需共享的图表选项应写入 spec；当前浏览器覆盖项可通过恢复默认清除。
- JSON/XML 导入导出复用同一 schema。HTML 是受限沙箱面板，通过声明的 query 数据桥取数；不能任意访问网络、读取凭据或修改应用外壳。

图表类型和字段绑定见 [charts.md](charts.md)，完整 HTTP 路径见 [api-contract.md](api-contract.md)。

## 个人与项目视图

创建请求支持顶层 `visibility:"personal"|"project"`，旧请求默认 project。响应与目录包含 visibility、owner_id、can_edit；owner_id 由服务端记录，不能由 spec 冒充。个人视图只对 owner 可见，且仍需项目读取权限和相应 dashboard scope。项目 viewer 可创建/编辑自己的个人视图，不能借此写共享视图；共享视图继续要求项目 edit 权限。

PUT 可省略 visibility 来保留原值；显式切换仅 owner 且具 dashboards:write 可用，切到 project 另须项目 edit 权限，变更与 spec 共用同一 If-Match/revision 事务。412 不改变可见性。历史、导出、校验、preview/apply/restore 与 HTML render 共用访问检查；个人变更只写 owner 的私有 SQL 事件流。project→personal 对项目流仅发送无对象 ID 的 reset_required，避免广播个人视图 ID。旧视图保持 project，owner 从首个已保存版本 actor_id 回填，无 actor 时不猜用户。

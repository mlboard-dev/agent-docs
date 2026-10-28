> 来源：[server/docs/following.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/docs/following.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 账号关注

关注属于登录用户，独立于比较选择、公开分享及通知订阅。支持会话 cookie 或原生 `Bearer <session_token>`；API key 不能访问关注接口。Bearer 会话仍须在修改时提供登录返回的 CSRF token 和合法 Origin，不会被当作免 CSRF 的 API key。

- `GET /api/v1/following?limit=100&cursor=...` 返回 `following`、`next_cursor` 和用户 `version`。每项含 run/project/incarnation、关注状态及 revision、更新时间、ETag、轻量 run metadata 和 project_name。按 run ID 分页，cursor 绑定用户及用户版本；版本变化返回 410，需要从第一页校准。
- `GET /api/v1/runs/{id}/following` 返回当前状态和 ETag。无记录为 `following:false,revision:"0"`。
- `PUT` / `DELETE /api/v1/runs/{id}/following` 的 JSON 必须含 `run_incarnation`，并用 `If-Match` 携带上次 ETag。缺条件为 428；冲突为 412，不覆盖新意图。同 incarnation、相同最终状态的旧 ETag 重试返回当前状态，不再递增 revision；方向相反的过期操作失败。重建对象使用新 ETag，旧 incarnation 返回 404。
- `GET /api/v1/following/updates` 为用户私有 SSE，支持十进制 `Last-Event-ID` / `cursor`。`following_changed` 含 run/incarnation、following、状态 revision 和用户 version；删除产生旧 incarnation 的 false/tombstone。共享 SQL 的用户事件日志支持多进程观察，约每秒检查一次，不通过项目 Hub 广播。

SSE 仅提示校准。缺 cursor、日志缺口或回退发送 `reset_required`；每 15 秒要求再次校准，以覆盖成员资格变化。前台恢复仍读取 API。每用户保留最近 1000 条私有事件，最多 1000 个当前可访问的 active follows；每实例最多 64 条此类流。撤权对象从列表隐藏，新关注写入会把不可访问的 active 记录转为 false 并发送私有 reset；保留小型 revision tombstone，避免已用 ETag 再次有效。用户也可凭自己已有的 Run incarnation 和 ETag DELETE 已撤权关注，此时仅返回原有关注状态，不含 `run`。Run 删除级联清除关注；不为新实例继承。关注不会自动开启 APNs 或项目状态通知。

state/list 内的 `run` 是轻卡片投影：`metadata_projection:"following"`，`config:{}`、`tags:[]`、`summary:{}`，不查询完整配置；需要配置时单独读取 Run。列表默认 100、最多 500 条，并在编码后限制每页 1 MiB，可能在条数上限前返回 `next_cursor`。

通知另外持久绑定 `run_incarnation`：新 Run 通知和 APNs 路由 hint 都含该字段；旧无可信身份的 Run 通知不再可读或投递。读取和投递前复核当前身份与授权，generic 推送测试不要求 Run 身份。

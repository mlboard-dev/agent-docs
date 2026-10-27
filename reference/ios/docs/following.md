> 来源：[ios/docs/following.md](https://github.com/mlboard-dev/ios/blob/d42eab1f37a90c5d171611f57556877f62e39fda/docs/following.md) · `d42eab1`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 原生关注与同步

登录后先进入“关注”。项目实验卡片和实验详情的星标操作同一账号集合，与比较勾选、项目通知订阅、APNs 授权均独立。取消关注可在关注页底部撤销；不会取消比较或停止实验。四个底部页签各有原生 `NavigationStack`；关注卡片、项目卡片和通知进入实验后，系统返回回到各自来源，通知不会借用关注页的路径。

## API 与身份

- `Run` 必须有 `run_incarnation`。缓存和待同步操作使用实例 URL、账号 ID、`run_id + project_id + run_incarnation`；列表卡片导航也携带期望 incarnation。详情不匹配时显示实验失效，不转向重建后的同 ID 实验。
- 图表与结构化历史查询在 `runs.run_incarnations` 传完整的 run ID → incarnation 对照表，由服务端在实际历史读取时隔离身份；不依靠客户端前后读取元数据替代该约束。
- `GET /api/v1/following?limit=100&cursor=…` 返回 `following`、`next_cursor`、账号 `version`。每行包含关注 state、轻量 `run` 和 `project_name`。分页间版本变化保留已确认列表并提示刷新。
- 轻量 `run` 的 `metadata_projection=following`，`config={}`、`tags=[]`、`summary={}`、`summary_status=not_requested`；配置与文件在进入详情后独立读取。成功 state 不要求附带 `run`，兼容撤权后清理自己旧关注的响应。
- `GET /api/v1/runs/{id}/following` 返回 `run_id`、`project_id`、`run_incarnation`、`following`、十进制字符串 `revision`、`updated_at`、`etag`。未关注的 revision 0 也必须先读取 ETag。
- `PUT` / `DELETE /api/v1/runs/{id}/following` 发送 JSON `{ "run_incarnation": "…" }`，使用上次 ETag 的 `If-Match`，表示明确的目标状态；不发送 toggle。成功响应为新 state。
- 412 后只读取最新 state，保留用户意图并停止自动提交。“确认关注 / 确认取消关注”才采用用户刚确认的新版本；“保留服务器状态”丢弃本地意图。旧版本列表和旧请求响应不能覆盖新点击。

不支持该接口的旧服务端显示更新提示，项目与指标入口仍可用。

## 前台、离线与边界

回到前台立即重验证，前台每 20 秒同步一次；进入后台停止轮询，退出账户取消在途同步。每次最多处理两个待同步实验，轮换队列避免单个失败项阻塞后续操作。没有后台常驻连接，也不依赖 APNs 保证关注同步。

待同步队列使用 `WhenUnlockedThisDeviceOnly` Keychain，最多 64 个实验，每个只保存最终目标状态、原 ETag、身份和必要卡片元数据。快速反向点击合并为最终意图；离线恢复先 GET：已达到目标则确认完成，版本变化但目标不同则要求明确确认。保存队列失败时不提交未记录的操作。注销清除队列和账号缓存，账号或实例切换不会复用旧任务。

列表每页 100 条，最多打开 10 页；刷新只重读已经打开的页数。元数据先显示，不等待摘要或指标历史。前六张卡片按需读取最多两个真实标量，每条 Step 趋势最多 40 个绘图点。主值单独读取精确 `summary.last`，不取降采样曲线最后一个点；迟到上报、非有限值和不同 context 不会混用。摘要和每条趋势分别重试，失败保留已确认数据，不阻断卡片元数据和详情入口。完整指标与参数仍在实验详情。

通知点击先刷新会话，再按通知 ID 读取当前有权限的通知与实验。实验通知必须有匹配的 `run_incarnation`；旧实验通知、删除和撤权均不能指向同 ID 重建的实验。无实验目标的普通通知允许不带 incarnation。

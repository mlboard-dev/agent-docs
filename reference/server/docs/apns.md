> 来源：[server/docs/apns.md](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/docs/apns.md) · `73643d8`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# iOS 推送与 APNs

服务器可选启用 APNs token provider。没有 Apple 凭据时保持关闭；收件箱和订阅仍然可用。测试使用本地 HTTP/2 模拟 APNs，不代表 Apple 或真机已接收、展示。

## 服务端配置

| 变量 | 含义 |
| --- | --- |
| `MLBOARD_APNS_ENABLED` | 默认 `false`；启用后启动时验证其余字段 |
| `MLBOARD_APNS_TEAM_ID` | Apple Team ID，10 位字母数字 |
| `MLBOARD_APNS_KEY_ID` | APNs signing key ID，10 位字母数字 |
| `MLBOARD_APNS_TOPIC` | 与 iOS bundle identifier 一致的 topic |
| `MLBOARD_APNS_ENVIRONMENT` | `sandbox`（默认）或 `production` |
| `MLBOARD_APNS_KEY_FILE` | 服务器可读的 PKCS8 PEM `.p8`，ES256/P-256 |

`.p8` 仅放在部署机的私有文件或只读 secret 挂载中，建议文件权限 `0600`。不要上传到 Git、前端、iOS 工程或 API。启用但配置无效会终止启动；禁用时不需要密钥文件。服务器出站访问 Apple HTTPS，使用 HTTP/2、15 秒请求超时和复用的 ES256 JWT；JWT 约 50 分钟更新。`ExpiredProviderToken` 可触发提前更新，但仍间隔至少 20 分钟；新 token 被立即报过期时暂停至下次允许更新时间，并检查主机时钟。配置示例见[部署说明](deployment.md)。

## 设备接口

以下路径均带 `/api/v1` 前缀，只接受账号会话。写请求同时需要 `Cookie: mlboard_session=...` 和 `X-CSRF-Token`；API key 不能注册设备。

- `GET /me/push-devices` 返回 `{enabled,paused_until,devices}`。设备包含 `id,name,environment,topic,locale,preview,updated_at,expires_at,disabled,last_status,last_reason,pending`；不返回 token。
- `PUT /me/push-devices/{installation_id}` 请求 `{token,environment,topic,name?,locale?,preview?:false}`。客户端安装 ID 保存在该安装的 Keychain；token 使用十六进制字符串。环境和 topic 必须与服务器一致。每账号最多 16 个设备；注册有效期最多 30 天且不超过绑定的登录会话。
- `DELETE /me/push-devices/{installation_id}` 撤销设备及其待投递记录；客户端在退出或撤销系统通知权限时调用。
- `POST /me/push-devices/{installation_id}/test` 返回 `202 {notification_id,status:"queued"}`，每账号每分钟一次。之后通过设备诊断判断 APNs 是否接受。测试记录也进入收件箱。

设备绑定具体登录会话，退出、密码轮换/重置或管理员撤销会话会级联删除其绑定和队列。重新登录需重新注册。相同 APNs token 在同环境/topic 仅保留一个绑定，避免切换账号后继续收到上一账号的通知。每次启动/回到前台检查系统授权并刷新绑定；拒绝授权不上传 token。

## 收件箱、订阅与隐私

- `GET /notifications?limit=100&cursor=...` 返回 `{notifications:[{id,kind,title,body,project_id,run_id,read_at,created_at}],next_cursor}`，每页默认/最多 200 条，按新到旧排列，并重新校验项目及组织权限。空 `next_cursor` 表示结束；游标不应由客户端解析。
- `GET /notifications/{id}` 返回 `{notification:...}`，适合直接定位超过收件箱第一页的旧推送。未知 ID、其他用户和已撤销的项目/组织权限均返回 404。
- `POST /notifications/{id}/read` 标记已读；待发推送随后取消。
- `GET /subscriptions`；`POST /subscriptions {project_id,events:["run_finished","run_failed","run_stopped"]}` 按用户/项目更新并返回稳定 `id`；`DELETE /subscriptions/{id}` 退订。

只有实验状态实际变化且匹配订阅时才生成通知，通知和每设备队列随状态事务提交。APNs 网络请求在 SQL 事务外执行；推送网络失败不回滚实验数据。发送前重新检查账号、会话、设备修订、组织/项目权限、订阅事件、已读和到期状态。历史通知尝试通过旧正文精确关联 run；无法关联的历史实验通知不再对外返回。

锁屏默认只显示 `MLBoard` 和通用状态提醒，不包含实验名称、路径、指标、配置或具体错误。用户显式设置 `preview:true` 才允许正文预览。payload 中 `mlboard:{notification_id,project_id,run_id}` 仅用于导航；App 必须向已信任的服务器重新鉴权、读取实际内容，不接受推送指定任意服务器地址。

## 队列和排查

worker 每秒最多串行处理 8 个任务，一次网络请求在途；数据库租约为 1 分钟。服务重启后保留队列，过期租约可重领。网络错误、429、5xx 和暂时的 provider token 错误最多尝试 8 次，指数退避加 jitter，并遵守至多一小时的 `Retry-After`；5xx 至少等待 15 分钟。下一次重试晚于 TTL 时立即取消。普通通知 TTL 为 24 小时，测试为 5 分钟；终态诊断保留 7 天。provider 认证错误会暂停实例发送至少一分钟，设备列表的 `paused_until` 可见该状态。

`last_status` 为 `queued`、`sending`、`accepted`、`failed` 或 `cancelled`。`accepted` 仅表示 APNs 接受，设备展示和送达仍未知。`last_reason` 不包含 token 或密钥。`BadDeviceToken`、topic 不匹配和当前 token 的 410 会停用相应注册；旧修订、旧注册时间或过期租约返回的 410 不能停用新绑定。

消息按至少一次处理：APNs 已接受而进程尚未写回就崩溃，可能重发。重试使用稳定 notification/collapse ID，客户端按 notification ID 去重。已经在途或被 Apple 接受的请求无法撤回；注销、撤权、退订和已读会停止后续发送。

协议参考：[Apple APNs 请求](https://developer.apple.com/documentation/usernotifications/sending-notification-requests-to-apns)、[APNs 响应](https://developer.apple.com/documentation/usernotifications/handling-notification-responses-from-apns)、[token 认证](https://developer.apple.com/documentation/usernotifications/establishing-a-token-based-connection-to-apns)。

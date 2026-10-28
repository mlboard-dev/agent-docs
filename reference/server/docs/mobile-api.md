> 来源：[server/docs/mobile-api.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/docs/mobile-api.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 原生 iOS API

原生 App 使用与 Web 相同的 `/api/v1` 数据接口、账号权限和会话策略；使用自己的实例 URL，通过 TLS 连接生产服务。GitHub/OIDC 登录通过 `ASWebAuthenticationSession`，provider 的 client secret 与 `.p8` 均只在服务器。

## 账号与 OAuth

`GET /auth/providers` 返回 `{providers:[{id,name,enabled}]}`；`id` 为 `password`、`github` 或 `oidc`。密码登录调用 `POST /auth/login {username,password}`，从响应获取 `{user,csrf_token}` 和 `mlboard_session` cookie，随后清空密码输入。

原生 OAuth 使用两个独立的 PKCE 流程：服务器对上游 provider 验证原有 state、浏览器绑定 cookie、PKCE 和 OIDC nonce；App 对本站一次性 code 验证自己的 S256 proof。

1. App 随机生成 43–128 字符的 RFC7636 verifier（`A–Z a–z 0–9 - . _ ~`）和 16–128 字符同字符集的独立随机 state。计算 `BASE64URL(SHA256(verifier))`，不带 padding。
2. 在系统认证会话中打开 `GET /auth/mobile/oauth/{provider}/start?code_challenge=...&state=...`，callback scheme 设为 `mlboard`。只支持已启用的 `github`/`oidc`。授权事务最多 10 分钟，绑定该浏览器 cookie。
3. 成功回调固定为 `mlboard://oauth?code=<opaque code>&state=<original state>`。服务器忽略调用者的 redirect URL。App 必须先验证 scheme、host 和 state，只向发起认证的同一个可信实例兑换 code。失败或取消可关闭系统浏览器，不把错误当作成功登录。
4. App 以 JSON 调用 `POST /auth/mobile/exchange {code,code_verifier}`。code 有效 90 秒，仅可成功使用一次；错误 proof 无法消费合法 grant。返回 `{user,session_token,csrf_token}`，同时设置 `mlboard_session` cookie。过期、重放、错误 proof、禁用账号或失效 provider 返回 `401 invalid_mobile_grant`。

callback 不创建浏览器登录会话、不携带本站长期凭据或上游 token。账号解析与普通 Web OAuth 一致：以 provider/issuer/client/subject 的稳定身份绑定，域名、端口或 HTTPS 回调变化不创建新账号；不同 subject 不按 email 合并；注册关闭时只允许已有绑定身份登录。

## 会话、数据与退出

App 将本站会话 token、CSRF 和绑定实例的资料保存在 Keychain。所有请求发送 `Cookie: mlboard_session=<session_token>`；写请求再发送 `X-CSRF-Token`。可发送与实例一致的 `Origin`；未发送 Origin 的原生请求允许通过，外国 Origin 会被拒绝。不要把本站会话作为 SDK API key/Bearer 使用。

`GET /auth/me` 校验现有会话并返回 `{user,csrf_token}`；会话有效期遵守实例凭据设置。此版本使用可撤销的服务器会话，没有额外的移动 access/refresh token。`POST /auth/logout` 撤销当前会话和其 APNs 绑定；App 同时清空 Keychain 凭据和私有缓存。`/auth/me` 返回 401 或 403 时表示会话不可用，应返回登录界面；普通项目接口的 403 可能只是资源权限不足，不能据此清除整个登录状态。

实验浏览使用 `GET /projects`、`GET /projects/{id}/runs`、`GET /runs/{id}`、`GET /runs/{id}/series` 和 `POST /projects/{id}/query`。通知和设备契约见 [APNs](apns.md)。推送内的 ID 只作导航定位；打开时重新读取收件箱/run，权限失效、实体删除或服务器离线均显示实际状态。

验证使用本地真实 HTTP OIDC provider，检查双层 PKCE、固定 callback、浏览器绑定、grant 过期/重放/并发兑换、禁用账号/provider、跨实例 Origin 和域名/端口变更后的稳定账号/权限。尚无 Apple 凭据或真实身份服务的测试结果时，不声称已验证真机 APNs 或生产 OAuth。

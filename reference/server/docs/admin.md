> 来源：[server/docs/admin.md](https://github.com/mlboard-dev/server/blob/4caeb73c2e0697158c5f376de000da3e6d523d78/docs/admin.md) · `4caeb73`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# Instance administration and recovery

Instance administration requires a real browser session, its CSRF token and same-origin requests. API keys cannot administer users or instance settings. Instance administration does not grant experiment data access; assign a project role explicitly in the organization project directory.

The user page can disable accounts, change instance administrator status and issue a short-lived one-time password reset ticket. Preserve the last active instance administrator and each organization/project's active owner. Credentials and ticket contents are never recorded in the audit log.

An operator with local/container access can recover an existing instance administrator:

```sh
mlboard admin list-admins
mlboard admin reset-password --username admin
```

Interactive input is hidden and confirmed twice. For Docker, reuse the service's existing database environment. Prefer an interactive terminal with hidden input and confirmation:

```sh
docker exec -it <container> /mlboard admin reset-password --username admin
```

For automation, use stdin without placing the password in argv:

```sh
read -r -s MLBOARD_NEW_PASSWORD
printf '%s\n' "$MLBOARD_NEW_PASSWORD" | docker exec -i <container> /mlboard admin reset-password --username admin --password-stdin
unset MLBOARD_NEW_PASSWORD
```

Use the actual container and binary names from your deployment. The reset uses `MLBOARD_DATABASE`, `MLBOARD_DSN`, `MLBOARD_DATA_DIR` or equivalent flags. It requires an account that already has instance administrator status, does not enable disabled accounts, and revokes that account's sessions, API keys and reset tickets atomically. It opens the database directly, so OAuth/configuration decryption errors cannot prevent local recovery. No reset command creates or promotes an ordinary account.

If the service was started with custom database/path flags instead of environment variables, supply the same flags to the recovery command. Recovery refuses in-memory or missing SQLite files and never initializes an empty database at a mistyped path.

The instance settings page manages instance name/description, default language/theme, registration, project creation/public sharing, credential lifetimes and GitHub/OIDC provider configuration. Registration is off by default and governs both password registrations and new OAuth subjects. Existing accounts continue to sign in when registration is disabled. Add new users to an organization and a project separately; signup grants neither.

Provider secret inputs never display stored values. Leaving a secret blank preserves it; use the explicit clear control to erase it. Only fully configured providers can be enabled. Credentials are encrypted in the database and audit records contain only changed field names. Concurrent settings editors use revisions so a stale save cannot overwrite a newer one.

Disabling public sharing immediately makes existing anonymous links, queries and media unavailable. Re-enabling it restores still-valid links; delete a link to revoke it permanently. Changes to session/key/share lifetimes apply to newly issued credentials; revoke existing ones separately if needed.

## 密钥期限与审计

实例设置的“密钥最长期限”可选“无限制”，对应 `credentials.key_max_days: 0`。
默认期限仍为有限天数；创建密钥时可选默认、指定日期或永不过期。永不过期需要实例允许，显式传 `never_expires: true`，不能同时传 `expires_at`。恢复期限上限只约束新建密钥，不会改写现有密钥。

`GET /api/v1/keys/policy` 向已登录浏览器提供当前密钥期限策略。
`GET /api/v1/admin/audit?limit=50&cursor=…` 提供稳定的时间/ID 游标分页，返回操作者 `actor`（用户名、显示名）与目标 `target`（类型、名称）。已删除对象保留原始 ID；这些名称表示当前资料，原始操作代码、ID 和详情始终可展开查看。

组织、项目至少保留一名有效所有者，实例至少保留一名有效管理员。违反约束的响应码分别是 `last_organization_owner`、`last_project_owner`、`last_instance_admin`；页面给出可操作的提示，请求 ID 收在诊断信息内。

## 升级旧 OAuth 身份映射

新版本将外部账号身份与回调地址分开保存。改变 `MLBOARD_PUBLIC_URL` 的域名、端口或 HTTPS 后，已迁移的账号仍保留原组织和项目权限；OIDC issuer/client ID 仍隔离，绝不按邮箱自动合并。

升级时若仍使用原 public URL，启动会自动迁移对应的旧身份键。如果在升级前或同时已经改了 public URL，旧键只有摘要，服务器不会猜测原域名。使用原始地址执行一次：

```sh
# 使用与运行服务相同的数据库配置；此前的 URL 只用于恢复旧身份键。
./mlboard admin migrate-oauth-identities --previous-public-url http://old-host:8080
# 容器内沿用部署的数据库环境：
docker exec <container> /mlboard admin migrate-oauth-identities \
  --previous-public-url http://old-host:8080
```

此命令根据当前保存的 provider issuer/client ID 和指定旧 URL 计算旧命名空间，原子迁移到稳定命名空间；可重复执行。若新旧映射指向不同账号，会拒绝迁移，不合并权限。原 issuer/client ID 也变更时需先确认正确的身份来源，不能通过尝试其他 issuer 把账号连接起来。

## 验证备份的设置密钥

备份工具可使用以下只读命令验证快照与恢复密钥是否匹配；它不迁移或修改快照：

```sh
./mlboard admin verify-settings-key --database sqlite \
  --dsn /private/backup/mlboard.sqlite --data-dir /private/backup
```

命令读取原 `MLBOARD_SETTINGS_KEY` 或指定目录的 `settings.key`，实际解密已保存的 OAuth 配置。密钥格式正确但不属于此实例同样失败；不要用新生成的 key 替换原 key。

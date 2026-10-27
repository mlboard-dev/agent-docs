> 来源：[server/docs/setup.md](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/docs/setup.md) · `73643d8`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# First startup

Start the binary or container with a persistent database and data directory, then open the configured public origin. A new database starts without accounts or experiments. Complete setup with an administrator username, a 15–128 character password, instance name and first organization name/slug. The administrator and first organization owner are created in one transaction; setup closes as soon as initialization succeeds.

Local username/password login remains available independently of OAuth. New accounts do not automatically join organizations or projects. An administrator must add organization membership and grant the required project role.

For direct HTTP setup, send `POST /api/v1/auth/setup` with `username`, `password`, `instance_name`, `organization_name`, `organization_slug` and optional `display_name`/`email`. Supply the same-origin `Origin` header. The response sets an HttpOnly session cookie and returns a CSRF token; use `X-CSRF-Token` for subsequent cookie-authenticated mutations.

See [organizations](organizations.md), [operator recovery](admin.md) and the [API contract](api-contract.md).

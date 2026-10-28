> 来源：[server/README.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/README.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# MLBoard server

Go service with embedded React/TypeScript Web, SQLite or PostgreSQL metadata/history adapters and private immutable artifacts. The initial deployment has no generated experiments. Uploaded files use configurable local/S3 storage; RustFS is the recommended S3 service.

For a standalone server deployment, start with [minimal binary and Docker Compose examples](docs/deployment.md). Both SQLite/local and PostgreSQL/RustFS samples live in this repository’s `deploy/` directory.

Query results use a bounded L1 cache by default; an optional Valkey overlay provides shared reuse without becoming an upload or authorization dependency. Persistent SQL projections remain opt-in (`off` by default, then `build` / `on`); covered scalar/step queries have a limited SQL sampling path. Configuration, upgrade credential invalidation and storage-epoch rotation after restore are documented in [deployment](docs/deployment.md) and [configuration](docs/configuration.md). These features are not a measured capacity guarantee.

From the enclosing workspace root:

```sh
python3 scripts/setup-go.py
./scripts/build.sh
./scripts/run.sh --listen 127.0.0.1:8766
```

The workspace pins Go 1.27.3 and uses installed Node 24. Build/cache/temp files stay under workspace `outputs/`. The resulting `outputs/bin/mlboard` serves the Web UI without a separate Node runtime. Open the chosen address and create the first local administrator. SQLite data and artifacts default to `outputs/runtime/` through the wrapper script.

Standalone binary options:

```sh
./outputs/bin/mlboard --listen 127.0.0.1:8766 --database sqlite \
  --dsn ./outputs/instance/mlboard.sqlite --data-dir ./outputs/instance/files
```

`--database postgres --dsn 'postgres://…'` selects PostgreSQL. Both adapters are exercised by the real HTTP/ingestion/migration/recovery Go suites; PostgreSQL tests use isolated random schemas in an explicitly configured validation database. `--web-dir` overrides embedded assets for development. Health endpoints are `/healthz` and `/readyz`.

## Identity configuration

Local username/password login is always available. OAuth providers are enabled only when configured; no demonstration authentication is provided.

| Variable | Meaning |
| --- | --- |
| `MLBOARD_PUBLIC_URL` | Trusted external origin and callback base, e.g. `https://experiments.example.org`; HTTPS enables secure cookies |
| `MLBOARD_GITHUB_CLIENT_ID` / `MLBOARD_GITHUB_CLIENT_SECRET` | GitHub OAuth application |
| `MLBOARD_OIDC_CLIENT_ID` / `MLBOARD_OIDC_CLIENT_SECRET` | OIDC relying party credentials |
| `MLBOARD_OIDC_ISSUER` | Discovery issuer URL |
| `MLBOARD_REGISTRATION_ENABLED=true` | First-start opt-in to local/OAuth new-account registration; persisted switch defaults false |

Register callbacks `<public origin>/api/v1/auth/oauth/github/callback` or `/api/v1/auth/oauth/oidc/callback`. Environment credentials seed persisted settings once; later changes use the instance settings page. Create the initial administrator locally before any registration. External identities bind by provider/subject, never automatically by email, and gain no project access or admin privilege. Organization administrators add members and grant project roles separately. OIDC discovery, signed ID tokens, PKCE, nonce, browser binding and state replay are covered by a local provider test; real provider credentials have not been used in validation.

## API and data

[Instance settings](docs/admin.md) persist registration, defaults, access policies and encrypted provider credentials. Back up the private settings key as described in [deployment](docs/deployment.md).

The [API contract](docs/api-contract.md) documents routes and shared shapes. Runtime `/api/v1/capabilities`, `/api/v1/schemas` and `/api/v1/registry` report actual supported versions and limits. Bearer keys and cookie sessions share live project authorization. Public share queries use a separate restricted principal.

Ingestion commits immutable event identities, typed history projections and revision watermarks together. SQLite uses WAL/FULL and a cancelable single writer gate; PostgreSQL uses transaction advisory locks per ingestion run. Queries have explicit budgets, canonical history selection, min/max downsampling and fixed paged snapshots. The `internal/store` typed history/coordinator boundary is intended for a later independent history backend, which would also need a publish/recovery protocol.

SSE and WebSocket carry project changes and invalidations; HTTP carries batched writes and queries. WebSocket supports one project per connection and no ingestion. `/mcp` is a thin JSON-RPC tools adapter over the same HTTP authorization and dashboard preview/apply operations.

HTML panels are separate sandboxed documents with no same-origin/network access. Only declared query results cross a bounded MessageChannel bridge. No token or arbitrary query capability is passed to the child. Optional APNs delivery uses a persistent queue, session-bound devices and server-owned signing credentials; native OAuth uses a fixed app callback and one-time PKCE exchange. Local simulated APNs/OIDC tests cover these paths; Apple credentials and real-device delivery remain unverified. Public dashboards, independent time-series databases and multi-resolution indexing are not implemented.

## Verification

Run `./scripts/verify.sh` from the workspace root after building dependencies. It checks Go, Web, Python, an isolated SQLite HTTP instance, actual SDK upload, backup/restart and design examples. Additional Go race tests and `go vet` are run with the workspace environment. See `docs/implementation-status.md` in the enclosing workspace for measured performance and unverified deployment areas.

## Program documentation

- [Setup and first organization](docs/setup.md)
- [Instance administration and password recovery](docs/admin.md)
- [Organizations and project permissions](docs/organizations.md)
- [Deployment: minimal binary, local Compose and PostgreSQL + RustFS Compose](docs/deployment.md)
- [Local / S3 artifact storage](docs/storage.md)
- [HTTP API contract](docs/api-contract.md)
- [Large scalar workloads and measured performance limits](docs/performance.md)
- [Persistent exact summaries and rebuildable SQL projections](docs/summary-projection.md)
- [Private account follows and conditional updates](docs/following.md)
- [iOS APNs configuration, devices and delivery diagnostics](docs/apns.md)
- [Native iOS OAuth and API sessions](docs/mobile-api.md)
- [Agent dashboard editing](docs/agent-dashboards.md)

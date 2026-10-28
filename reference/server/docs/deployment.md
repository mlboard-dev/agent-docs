> 来源：[server/docs/deployment.md](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/docs/deployment.md) · `15f9b75`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 部署 MLBoard Server

局域网 IP、公开地址与域名反代配置见 [lan-and-proxy.md](lan-and-proxy.md)。

服务端是一个内嵌 Web 的 Go 程序。数据库选择 SQLite 或 PostgreSQL；上传文件独立选择 **local 或 S3**，推荐用 RustFS 提供 S3 服务。运行时不需要 Node、Python、外部缓存或独立时序库；默认已有进程内查询结果缓存，可选 Valkey 共享缓存。

以下命令从 **server 仓库根目录**（工作区的 `src/server`）执行。`deploy/` 是部署配置与镜像锁的权威来源；外层工作区的 `deploy/` 只保留兼容入口，引用此处的服务和 Dockerfile。参数优先级、运行配置与首次初始化配置见 [configuration.md](configuration.md)。

## 1. 最简：SQLite + 本地文件

已有编译好的二进制时，直接运行：

```sh
./mlboard --listen 127.0.0.1:8080 \
  --database sqlite --dsn ./data/mlboard.sqlite \
  --data-dir ./data/files --artifact-storage local \
  --public-url http://127.0.0.1:8080
```

打开 `http://127.0.0.1:8080`，首次 `/setup` 创建实例、首个组织和管理员。新实例没有 demo 数据，默认不开放注册。数据在 `data/`，保留目录即可重启；运行过程中不要单独复制活跃 SQLite 主文件作为备份。

从源码构建可使用外层工作区 `scripts/build.sh`，或在 server 仓库运行：

```sh
mkdir -p outputs/tmp outputs/cache/npm outputs/cache/go-build outputs/cache/go-mod
export TMPDIR="$PWD/outputs/tmp"
export npm_config_cache="$PWD/outputs/cache/npm"
export GOCACHE="$PWD/outputs/cache/go-build"
export GOMODCACHE="$PWD/outputs/cache/go-mod"
# 使用已安装且满足 go.mod/package.json 要求的 Go 与 Node。
npm --prefix web ci --no-audit --no-fund
npm --prefix web run build
CGO_ENABLED=0 GOTOOLCHAIN=local go build -trimpath -o outputs/mlboard ./cmd/mlboard
./outputs/mlboard --data-dir ./outputs/data --listen 127.0.0.1:8080 \
  --public-url http://127.0.0.1:8080
```

Web 源码构建后嵌入二进制；之后运行只需二进制、数据及部署配置。工作区开发使用已有 `scripts/env.sh`，避免在全局环境安装依赖。

发布 Linux、macOS 或 Windows 的 amd64/arm64 二进制可用 [CGO 关闭的交叉编译入口](cross-compilation.md)。该脚本使用已有 Go，逐一验证产物的内嵌平台设置与 SHA-256，并把缓存、临时文件和产物集中在仓库输出目录。

## 2. 最简 Docker Compose：一个应用容器

完整文件：[deploy/compose.local.yml](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/deploy/compose.local.yml)。使用 SQLite + local，不需要外部服务。

以下示例固定项目名 `mlboard`。首次部署多实例时，为每个实例选不同的 `-p`；同一实例的启动、更新、exec 和停机始终沿用原名。已有部署应使用 `docker compose ls` 中现有的项目名，改名会选择另一组数据卷。

SQLite 的排序临时文件使用数据卷内的 `/data/files/sqlite-tmp`；旧卷缺少该目录时，应用以运行用户创建并验证可写。更新时需同时更新 Compose 模板，避免继续使用容器仅 64 MB 的通用 `/tmp`。该目录仍消耗磁盘空间和 I/O，不能将临时目录可写等同于容量无限。

```sh
cp deploy/.env.example deploy/.env
# local 模式无需填写 PostgreSQL 和 RustFS 凭据。
docker compose -p mlboard --env-file deploy/.env -f deploy/compose.local.yml up --build -d
```

等效的核心配置如下；仓库文件还包含非 root、只读容器根文件系统等设置：

```yaml
services:
  app:
    build:
      context: ..
      dockerfile: deploy/Dockerfile
    ports:
      - "127.0.0.1:8080:8080"
    environment:
      MLBOARD_DATABASE: sqlite
      MLBOARD_DSN: /data/mlboard.sqlite
      SQLITE_TMPDIR: /data/files/sqlite-tmp
      MLBOARD_DATA_DIR: /data/files
      MLBOARD_ARTIFACT_STORAGE: local
      MLBOARD_PUBLIC_URL: http://127.0.0.1:8080
    volumes:
      - mlboard-data:/data
volumes:
  mlboard-data:
```

## 2.1 PostgreSQL + 本地文件

需要 PostgreSQL、文件仍保存在应用卷时，使用 [deploy/compose.postgres.yml](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/deploy/compose.postgres.yml)。只需设置 `MLBOARD_POSTGRES_PASSWORD`，无需 RustFS 凭据：

```sh
docker compose -p mlboard --env-file deploy/.env -f deploy/compose.postgres.yml up --build -d
```

此入口和完整模式共用 PostgreSQL 服务及应用配置，保留 `mlboard-files`、`postgres-data` 卷。

## 3. 完整 Docker Compose：PostgreSQL + RustFS

完整文件：[deploy/compose.full.yml](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/deploy/compose.full.yml)，三项服务均在同一 Compose 网络。应用通过 `http://rustfs:9000` 读写 S3；数据库和 S3 API 端口不发布到宿主机。

```sh
cp deploy/.env.example deploy/.env
```

编辑 `deploy/.env`，设置以下非空且独立的凭据。不要使用文档占位值：

```dotenv
MLBOARD_PORT=8080
MLBOARD_PUBLIC_URL=
MLBOARD_POSTGRES_PASSWORD=<独立随机密码>
RUSTFS_ACCESS_KEY=<只含大写字母和数字的随机标识>
RUSTFS_SECRET_KEY=<独立随机密钥>
RUSTFS_CONSOLE_PORT=9001
MLBOARD_S3_BUCKET=mlboard-artifacts
MLBOARD_S3_CREATE_BUCKET=true
```

留空 public URL 会按 `MLBOARD_PORT` 派生 `http://127.0.0.1:<端口>`；对外部署应填写真实 HTTPS origin。然后运行：

```sh
docker compose -p mlboard --env-file deploy/.env -f deploy/compose.full.yml up --build -d
docker compose -p mlboard --env-file deploy/.env -f deploy/compose.full.yml ps
curl --fail http://127.0.0.1:8080/readyz
```

- MLBoard：`http://127.0.0.1:8080`，首次完成 setup。
- RustFS 控制台：`http://127.0.0.1:9001`，用 `.env` 中的 RustFS 凭据登录。
- `MLBOARD_S3_CREATE_BUCKET=true` 是样本中显式启用的首次建桶便利项；建好私有 bucket 后可改为 false。服务本身默认 false，不会设置 public bucket 策略。
- Compose 样本使用部署者提供的 RustFS 凭据。需要更细权限时，为应用建立专用 bucket/prefix 凭据，按 [storage.md](storage.md) 配置；不要向 SDK 或浏览器发放 S3 凭据。

持久化卷：

| 卷 | 内容 |
| --- | --- |
| `postgres-data` | 账号、项目、历史数据、附件引用和配置等 SQL 数据 |
| `rustfs-data` | 上传对象及 RustFS 自身元数据 |
| `mlboard-files` | settings.key、上传暂存及切换前的 local 历史文件 |

`docker compose down` 保留卷；`down -v` 会删除对应实例的数据，不用于正常重启。更新程序使用 `up --build -d`，不要删除卷。应用构建只使用此仓库的 `deploy/Dockerfile`；基础镜像及 RustFS/PostgreSQL 均固定 digest，唯一记录见 [images.lock.json](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/deploy/images.lock.json)。这套样本是单机部署，RustFS 仅一个数据卷，不提供多节点容灾。

## 3.1 可选 Valkey 共享查询缓存

默认仅有 L1，无需额外服务。需要进程重启或多应用进程间复用相同版本的查询结果时，优先叠加 [deploy/compose.valkey.yml](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/deploy/compose.valkey.yml)，可用于 local、postgres 或 full 任一入口。沿用该实例已有的项目名和 `.env`，用 `openssl rand -hex 24` 生成独立口令，填入 `VALKEY_PASSWORD`，并将 `.env` 权限设为 0600。使用 hex 避免口令中的 URL 保留字符；不要复用数据库或 S3 凭据。

```sh
# deploy/.env 中设置 VALKEY_PASSWORD=<生成的48位hex>，保留其他原有配置。
chmod 600 deploy/.env
docker compose -p mlboard --env-file deploy/.env -f deploy/compose.full.yml \
  -f deploy/compose.valkey.yml up --build -d
```

SQLite 或 PostgreSQL/local 部署将第一个文件替换为 `compose.local.yml` 或 `compose.postgres.yml`，后续更新、exec、停机沿用同一组 `-f`。overlay 为 app 设置 `MLBOARD_VALKEY_URL=redis://default:<hex-password>@valkey:6379/0`；`redis://` 是标准协议字符串，实际服务是 Valkey。连接已有 Valkey 可直接设置 `MLBOARD_VALKEY_URL` 而不用 overlay，外部 TLS 端点可用 `rediss://`。Redis 是协议兼容选项，不要求 Redis Stack 模块。

样本固定 Valkey 镜像 digest，不发布宿主机缓存端口；数据集上限 128 MiB、LRU 淘汰，容器上限 256 MiB/1 CPU，关闭快照与 AOF，重启后允许缓存丢失，无需备份缓存。应用不等待 Valkey 健康才启动，`/readyz` 仍检查数据库和文件存储。默认 L1 为 64 MiB、单项 2 MiB、TTL 300 秒；共享缓存每次操作默认 20ms，连续两次错误熔断五秒后再试，失败回源。开关、配额与观测见 [configuration.md](configuration.md)。

SQL 事务仍负责原始事件和 durable ACK，local/S3 仍负责上传文件。缓存只保存可丢弃的查询结果，每次仍从 SQL 检查权限和不可变身份；添加 Valkey 不会绕过授权，也不能替代冷数据查询优化。

## 4. 使用已有 PostgreSQL / S3

数据库和对象存储可独立组合；例如 SQLite + RustFS 也支持。连接已有 S3 服务时：

```sh
export MLBOARD_ARTIFACT_STORAGE=s3
export MLBOARD_S3_ENDPOINT=https://objects.example.com
export MLBOARD_S3_BUCKET=mlboard-artifacts
export MLBOARD_S3_REGION=us-east-1
export MLBOARD_S3_PREFIX=mlboard/artifacts
export MLBOARD_S3_PATH_STYLE=true
# 从部署 secrets 注入以下文件，勿把实际密钥放进命令历史。
export MLBOARD_S3_ACCESS_KEY_FILE=/run/secrets/s3_access_key
export MLBOARD_S3_SECRET_KEY_FILE=/run/secrets/s3_secret_key
./mlboard --database postgres --dsn 'host=postgres dbname=mlboard user=mlboard sslmode=require' \
  --data-dir /data/files --listen 0.0.0.0:8080 \
  --public-url https://mlboard.example.com
```

PostgreSQL 密码可通过 `PGPASSWORD` 注入。S3 完整参数、旧文件兼容、Range/HTML、备份和切换语义见 [storage.md](storage.md)。配置为 `rustfs` 会被拒绝；正确值是 `s3`。

## 5. 访问入口与运行管理

默认 Compose Web 端口只绑定宿主机 loopback；对外使用 HTTPS 反向代理，将同一个域名的 Web、`/api/`、`/mcp` 和实时连接统一转发给应用。保留正确 Host，配置与用户实际访问地址一致的 `MLBOARD_PUBLIC_URL`。代理需支持 SSE/WS，并调整上传请求体上限（256 MiB 文件加 multipart 开销）和超时。HTTPS public URL 自动启用 Secure cookie。

代理后的客户端限流需显式设置 `MLBOARD_TRUSTED_PROXIES`，填写应用实际看到的 socket 代理 CIDR；默认不信任任何转发头。代理应清除外来 `X-Forwarded-For` 或追加真实来源，应用只从可信右侧 hop 解析此头，不据此改变 Host/HTTPS/Origin。普通 JSON、上传、有限响应使用独立时限；上传默认全局 8、每账号 2、每项目 4 并发。详见[请求与上传边界](request-boundaries.md)及[运行配置](configuration.md)。

- `/healthz`：进程存活。
- `/readyz`：数据库和已配置文件存储可用；S3 bucket 不可达时返回 503。
- 实例管理 → 实例设置：注册开关、访问策略、默认显示、密钥期限和 OAuth。
- 实例管理 → 实例状态：数据库、当前文件写入后端和详细运行信息，不显示 S3 密钥。
- 设置及注册邀请说明见 [admin.md](admin.md)、[setup.md](setup.md)、[organizations.md](organizations.md)。

容器内恢复已有管理员密码：

```sh
docker compose -p mlboard --env-file deploy/.env -f deploy/compose.full.yml exec app \
  /mlboard admin reset-password --username admin
```

local 样本替换 Compose 文件名即可。命令隐藏输入并确认密码，会撤销该管理员旧会话和 API key；不创建新管理员、不启用禁用账号。自动化可使用 `--password-stdin`。

## 6. 数据库升级与备份

启动时执行可重复的增量迁移。v3 增加单次注册邀请及本地邮箱登录别名；v4 增加附件存储后端/位置，旧记录明确归为 local。修改存储配置不会搬迁旧对象。升级前保留数据库与对象的一致备份，先在副本验证；不要将新 schema 直接交给旧程序回滚。

从不含 `run_incarnation` 的版本升级时，迁移为现有 Run 建立不可复用身份。历史公开分享和 `run_ids` 非空的静态 Run 限制 API key 没有可信身份绑定，会失效，需由有权限的用户重新创建并分发；不按当前同名 ID 猜测旧授权。宽范围的项目/全局 key 保持原 scope 语义。旧分页快照清除后重新查询。回滚版本也须保留这些身份/权限修复。

SQLite 使用 WAL/FULL 和单写入协调；PostgreSQL 使用事务及按 run 的写入锁。文件和数据库分离，备份须同时包含 SQL 快照、被引用对象及配置密钥。文件不作为静态公开目录，不直接暴露 RustFS bucket。具体备份边界见 [storage.md](storage.md#备份)。

首次保存 OAuth secret 会创建 `<data-dir>/settings.key`（0600、base64 32 字节 AES key），数据库只保存 AES-GCM 密文。也可通过 `MLBOARD_SETTINGS_KEY` 注入同一密钥；环境值优先于文件。原 key 缺失或错误会阻止解密，不自动生成替代。备份必须保留原 key；管理员本地密码恢复不依赖 OAuth 解密。

推荐使用 `MLBOARD_BOOTSTRAP_GITHUB_*`、`MLBOARD_BOOTSTRAP_OIDC_*` 和 `MLBOARD_BOOTSTRAP_REGISTRATION_ENABLED` 初始化新实例；兼容原来的不带 `BOOTSTRAP_` 名称。它们只在数据库尚无持久设置时生效，之后通过 Web 修改。`MLBOARD_PUBLIC_URL`、settings key、APNs 和文件存储属于运行配置，重启读取；完整规则见 [configuration.md](configuration.md)。

### 恢复后轮换 storage epoch

整库恢复或导入之前停止所有应用实例和写入，保持数据库、被引用文件与原 settings key 一致；恢复完成后、开放流量前，针对恢复后的数据库执行同版本命令：

```sh
./mlboard admin rotate-storage-epoch --database sqlite \
  --dsn ./data/mlboard.sqlite --data-dir ./data/files
```

PostgreSQL 使用相同命令，改为目标库的 `--database postgres` 和 DSN（或原部署环境变量）。Compose 可在 app 已停止、数据库仍运行时，用原项目名、`.env` 和全部 overlay 执行 `run --rm --no-deps app admin rotate-storage-epoch`；镜像已有 `/mlboard` entrypoint。完成后重启所有应用实例，再切换流量。

轮换会生成新缓存命名空间，清除分页快照、使公开分享与静态 Run 限制 key 的 grant 失效，需重新签发；不需要清空或共享管理员权限去执行 Valkey `FLUSHALL`。它不删除原始历史和上传文件，正常重启保留 epoch。

外层工作区 `scripts/sqlite-backup.py restore <backup> --destination <新目录>` 会在发布恢复目录前自动轮换 epoch 并失效上述旧引用，无需再重复运行该命令；脚本仅操作工作区内路径。手工 SQLite 恢复、PostgreSQL 恢复或其他导入工具需显式执行轮换。备份的原始 key 仍必须保留，epoch 不能替代加密密钥。

### 持久投影逐步启用

`MLBOARD_SUMMARY_PROJECTION` / `--summary-projection` 默认 `off`。可先用 `build` 分块追平并核对，再改为 `on` 切读；三种模式都保持摄取事务的 dirty 水位。覆盖不足仍回源，不能用滞后摘要冒充当前 exact。SQLite 一个 worker、PG 两个，每批可取消，数据目录文件系统少于 8 GiB 可用空间时暂停构建；另监测远端 PG 的磁盘。当前 cold-step 覆盖局限与回退见 [summary-projection.md](summary-projection.md)，开启并不代表所有轴或历史查询均加速。

## 7. 可选 APNs

默认 `MLBOARD_APNS_ENABLED=false`，无需私钥或 secret。启用前在 `.env` 中填写 `MLBOARD_APNS_TEAM_ID`、`MLBOARD_APNS_KEY_ID`、`MLBOARD_APNS_TOPIC`，并选择 `MLBOARD_APNS_ENVIRONMENT=sandbox` 或 `production`。私钥使用 [compose.apns.yml](https://github.com/mlboard-dev/server/blob/15f9b7577ce00934246e1e0b7ae219809b1b1590/deploy/compose.apns.yml) 的只读 secret 挂载：

```sh
export MLBOARD_APNS_PRIVATE_KEY_FILE=/absolute/private/path/AuthKey.p8
docker compose -p mlboard --env-file deploy/.env -f deploy/compose.full.yml \
  -f deploy/compose.apns.yml up --build -d
```

该 override 设置 enabled 和 `/run/secrets/mlboard_apns_key`，也可配合 local/PostgreSQL 入口使用。文件需能被容器 UID 65532 读取；本机 Compose 文件 secret 保留宿主文件权限，`uid/gid/mode` 可能不重映射。可将可读文件放在仅部署者能进入的私有目录中；不要放进源码构建上下文、镜像或 `.env`。无效启用配置会启动失败。设备绑定与实际投递边界见 [apns.md](apns.md)。

## 8. 验证

工作区 `scripts/verify-rustfs.py` 使用独立 RustFS 容器，执行真实对象读写、Range/权限/HTML、客户端上传与重启验证；`scripts/verify-postgres.py` 覆盖实际 PG race/HTTP/SDK、迁移、重启和恢复。

```sh
# 从工作区根目录执行，先准备已构建的二进制/容器镜像。
python3 scripts/test_run_config.py
python3 scripts/test_deployment.py --server src/server
python3 scripts/verify-rustfs.py --server src/server
python3 scripts/verify-containers.py --image mlboard:local --server-deploy src/server/deploy
```
测试数据和日志留在工作区 outputs，测试仅清理自己创建的容器、卷或随机 schema。

Go 单独运行时，`MLBOARD_TEST_POSTGRES_DSN` 必须指向专用验证数据库；每个测试创建随机 schema 并仅清理该 schema。不设置时使用 SQLite。当前不承诺大规模容量或多节点高可用；默认运行不引入独立时序库。

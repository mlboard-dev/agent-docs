> 来源：[server/docs/storage.md](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/docs/storage.md) · `73643d8`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 上传文件存储

配置只有 **`local` / `s3`**；RustFS 是推荐的 S3 兼容服务端，不是另一种存储协议。SQLite/PostgreSQL 继续保存附件元数据，文件内容由对象存储适配层读取。Python SDK 和浏览器上传/读取接口无需变化。

## 配置

| 环境变量 | 默认值 / 用途 |
| --- | --- |
| `MLBOARD_ARTIFACT_STORAGE` | `local`；设为 `s3` 启用远端对象写入 |
| `MLBOARD_DATA_DIR` | 本地持久目录，包含旧 local 对象、上传暂存及 settings.key；S3 模式仍需要 |
| `MLBOARD_S3_ENDPOINT` | S3 API origin，例如 `http://rustfs:9000`；不是 9001 控制台地址 |
| `MLBOARD_S3_BUCKET` | 已创建的私有 bucket 名称 |
| `MLBOARD_S3_REGION` | `us-east-1`，签名区域 |
| `MLBOARD_S3_PREFIX` | `mlboard/artifacts`，新文件的对象 key 前缀 |
| `MLBOARD_S3_PATH_STYLE` | `true`，RustFS 默认使用路径式地址；支持虚拟主机时可设 false |
| `MLBOARD_S3_ACCESS_KEY` / `MLBOARD_S3_SECRET_KEY` | S3 凭据，不放在命令参数、前端或数据库中 |
| `MLBOARD_S3_SESSION_TOKEN` | 可选临时凭据 session token |
| `MLBOARD_S3_CREATE_BUCKET` | `false`；显式设 true 时启动时创建缺失 bucket，不添加公开策略 |

三项凭据也支持同名加 `_FILE` 指向部署 secrets 文件；同一项不能同时设置环境明文和文件。服务不自动读取主机 AWS profile，也不查询实例 metadata 凭据。

非秘密参数有对应 CLI：`--artifact-storage`、`--s3-endpoint`、`--s3-bucket`、`--s3-region`、`--s3-prefix`、`--s3-path-style`、`--s3-create-bucket`。CLI 优先于环境。凭据只能通过环境或文件注入。端点必须为 HTTP(S) origin，不含用户名/密码、路径、query 或 fragment；不会跟随重定向发送凭据。

实例管理 → 实例状态显示当前写入后端；完整状态包含 endpoint/bucket/prefix，但不返回密钥。存储连接配置属于部署配置，修改后重启服务；不会在 Web 设置中隐式搬迁现有文件。`/readyz` 检查数据库、本地目录及已配置 S3 bucket 的可用性，S3 不可达返回 503，`/healthz` 只检查进程存活。

## 切换与历史文件

Schema v4 为每条附件增加 `storage_backend`、`storage_location`，已有记录默认是 local。S3 文件记录 endpoint、bucket 和完整 key，不存储凭据；对象 key 前缀不是 run 的分类路径。

- local → s3：新上传写 S3，旧文件继续从原 `<data-dir>/artifacts` 读取；保留原数据卷。
- s3 → local：新上传写本地；保留 S3 endpoint/凭据配置以便继续读取原 S3 对象。
- 更改新文件的 bucket/prefix：旧记录仍使用原 bucket/key；凭据须继续有旧 bucket 的读取权限。
- 更换 endpoint：没有自动数据搬迁。旧记录不匹配新 endpoint 时明确失败，不从另一个位置猜测同名对象；应先迁移对象和其元数据，或保持原 endpoint 地址。

当前支持一个配置好的 S3 endpoint 和 local 并存；没有历史对象批量迁移 CLI、多端点注册或自动垃圾回收。切换默认后端不等于迁移。

## 读写与权限

上传上限仍为 256 MiB，同时最多 8 个上传。请求先流式写有界暂存文件并计算 SHA-256，再写私有 S3 对象并等待成功；最后短事务提交 SQL 元数据。暂存、远端请求与清理均不持有数据库事务。训练事件引用文件前，客户端先完成文件上传。

S3 使用 AWS SDK v2/SigV4、显式 SHA-256 校验与不可覆盖对象名。相同 artifact ID/内容/元数据重试返回原记录，不产生逻辑副本；冲突不能覆盖。竞争或失败产生的本次临时对象会尝试清理；SQL 提交状态不确定时先检查引用，数据库不可用则保留对象，避免误删已提交文件。进程在对象发布与 SQL 提交之间崩溃可能遗留无引用对象，当前没有后台清理器。

内容通过 MLBoard API 代理，先检查登录权限或分享投影，再打开对象；不会生成跳过后续撤权的公开/预签名 URL。支持 HEAD、ETag 条件读取及 Range，S3 reader 只请求所需位置并使用有界缓冲。多范围最多 16 段。HTML 附件同样使用此接口，保留 256 KiB 渲染上限、digest 校验和 sandbox CSP。

通常给应用专用凭据授予目标 bucket/prefix 的 `s3:GetObject`、`s3:PutObject`、`s3:DeleteObject`，并授予 `s3:ListBucket` 供 HeadBucket 检查；启用建桶还需 `s3:CreateBucket`。完整 Compose 为首次安装复用部署提供的 RustFS 凭据；正式部署可在 RustFS 建立专用策略/凭据，预建 bucket 后禁用自动建桶。

## 备份

始终备份同一实例的 SQL 数据、被引用的不可变对象及 settings.key（或外部注入的同一密钥）。密钥必须能解密快照内 OAuth 密文，不能只验证 base64 长度或文件 hash；原 key 缺失或不匹配时恢复服务会拒绝启动。S3 不是数据库备份；本地文件卷在混合存储模式下仍包含历史对象和配置密钥。

外层工作区 `scripts/sqlite-backup.py` 只打包 local 文件，并在发布完整备份前调用 server `admin verify-settings-key` 验证密钥与快照匹配。`MLBOARD_BACKUP_VERIFIER` 可指定同版本二进制，默认使用工作区 `outputs/bin/mlboard`。发现任何 S3 记录时明确拒绝生成“完整备份”，避免漏掉远端文件。S3 模式应使用一致 SQL 快照（SQLite online backup 或 PostgreSQL pg_dump）加 bucket 的私有备份/复制，并核验快照引用的 size/SHA-256；当前未提供统一跨 SQL/S3 的备份 CLI。恢复保持原 endpoint/bucket/key 映射，先在隔离实例验证附件和 HTML 可读，再切换访问入口。

恢复/导入后开放流量前须轮换 storage epoch，防止新数据分支复用恢复前的查询缓存或分页快照。工作区 `sqlite-backup.py restore` 已自动处理；手工恢复或 PostgreSQL 使用同版本 `mlboard admin rotate-storage-epoch`。轮换使旧公开分享和静态 Run 限制 key 的 grant 失效，需重新签发；先停应用、完成恢复和轮换，再重启全部实例。命令与操作顺序见 [deployment.md](deployment.md)。Valkey 只有可丢弃结果，无需纳入数据备份。

部署样本见 [deployment.md](deployment.md)。实现参考 [RustFS Go SDK](https://docs.rustfs.com/en/developer/sdk/go) 和 [AWS SDK v2 endpoint 配置](https://docs.aws.amazon.com/sdk-for-go/v2/developer-guide/configure-endpoints.html)。

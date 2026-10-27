# 快速开始

需要实例地址、已有账号及组织/项目成员权限。普通登录账号可创建组织并成为所有者；实例管理员访问其他组织也要先加入。创建或选择项目后取得稳定 project ID。

1. 在项目中打开“接入实验”或账号的“API 密钥”，创建覆盖任务的项目 key。训练 key 不自动具有 Dashboard / HTML 权限。
2. 把实例地址配置为 `MLBOARD_SERVER`，将 key 通过秘密管理注入 `MLBOARD_API_KEY`。本仓库示例另外使用 `MLBOARD_PROJECT_ID`、`MLBOARD_RUN_ID`、`MLBOARD_DASHBOARD_ID` 作为任务参数。
3. 先读 `/api/v1/capabilities`、`/registry`、`/schemas`。REST 数据接口使用 `Authorization: Bearer <key>`，MCP 使用相同 key。
遇到鉴权前的`untrusted_host`时，检查[Host模式与反代配置](deployment.md)。宽松Host不会跳过API key权限。

4. 用 `GET /api/v1/projects` 核对项目可见性，再按 [训练接入](training.md)、[数据查询](querying.md) 或 [分析方案](dashboards.md) 操作。

安装 SDK 用 [py-client 源码仓库](https://github.com/mlboard-dev/py-client) 的已检查版本，安装到自己的虚拟环境。不要假设包已经发布到 PyPI。源码仓库为 Private，克隆需要获授权的 GitHub 账号。

```sh
git clone https://github.com/mlboard-dev/py-client.git vendor/mlboard-py-client
git -C vendor/mlboard-py-client checkout --detach 9f27e9de3d37b61a0276c71aec0e514d88759761
python3 -m venv .venv
.venv/bin/python -m pip install ./vendor/mlboard-py-client
```

实际 clone 路径、虚拟环境和数据目录应遵守目标项目约定。本仓库不保存实例密码、预置 API key 或可用项目 ID。

[完整 SDK](../reference/py-client/docs/sdk.md) · [同步与权限](../reference/py-client/docs/sync-and-keys.md) · [权限模型](permissions.md)

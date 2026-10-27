# 当前协议示例

这些是可替换的模板，不包含真实账号、项目、Run、Dashboard、preview或key。不要原样向生产实例写入。

| 文件 | 用途 |
|---|---|
| [train.py](train.py) | SDK接入：明确的10点合成验证、receipt与remote finish |
| [query.json](query.json) | 单Run标量查询；原始context/轴、incarnation及有限预算 |
| [dashboard.json](dashboard.json) | 一张曲线的DashboardSpec，供REST创建/校验 |
| [change.json](change.json) | 命名布局变更，base_revision需来自实际GET |
| [html-panel.json](html-panel.json) | HTML面板及显式字段能力；html字段要替换为源码 |
| [html-panel.html](html-panel.html) | 只消费q_loss声明数据的沙箱示例 |
| [mcp-initialize.json](mcp-initialize.json) | 初始化HTTP JSON-RPC |
| [mcp-list-tools.json](mcp-list-tools.json) | 读取当前工具目录 |
| [mcp-tool-call.json](mcp-tool-call.json) | 调用capabilities，无项目写入 |

query/dashboard模板中的 `run_REPLACE`、`inc_REPLACE`、`prj_REPLACE`、`dsh_REPLACE` 必须换成真实读取到的身份。查询只有一个Run，预算max_runs/max_series也相应为1；增加选集时同时检查总预算。change模板中的p_loss、revision与位置要按已有spec替换，不能覆盖其他面板。

创建方案body是 `{ "title": "示例方案", "visibility": "personal", "spec": <dashboard.json> }`；读取已有方案时使用服务器给出的真实ID。HTML通过同一preview/apply流程新增，另须html权限。数据返回值和preview ID不写进这些模板。

结构验证不能代替服务端的语义、身份、权限及布局校验。实测范围见 [VALIDATION.md](../VALIDATION.md)。

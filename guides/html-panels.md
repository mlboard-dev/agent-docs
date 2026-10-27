# HTML 沙箱面板

HTML是分析方案内的一张面板。它在独立sandbox iframe运行内联HTML/CSS/JS，不能读取主站DOM/凭据或联网加载CDN，也不能替换整站页面。公开分享当前不提供HTML面板。

1. 按 [分析方案流程](dashboards.md) 准备 type=html、plugin_version="1" 的面板。
2. 把 [HTML示例](../examples/html-panel.html) 内容作为 options.html；也可上传HTML artifact并使用其实际ID、版本、摘要。
3. 声明query_refs，并在options.capabilities逐个指定query_ref、fields、max_rows。没有声明就没有数据权限。
4. preview检查后按授权apply，打开已保存方案。直接打开HTML文件只会等待宿主，没有数据；当前preview API验证配置/diff，并不运行交互式草稿HTML。

[面板配置模板](../examples/html-panel.json) 与HTML文件都使用q_loss。模板的html为占位值，提交前替换为文件内容。数据字段使用x而非固定Step，同时允许value_state。当前HTML绑定字段白名单为run_id、step、x、value、value_state、event_ref、payload；不能直接声明elapsed_seconds。需要展示训练耗时，可把查询轴设为elapsed_seconds并读取x。

## 数据桥

宿主向目标iframe发送 `type:"init"`、protocol=`mlboard.html-bridge/v1`、instance_id、nonce和一个MessagePort。子页面只接收来自parent的初始化，之后通过该port交流。每个请求使用唯一request_id，并原样带回protocol/instance_id/nonce。

```json
{"protocol":"mlboard.html-bridge/v1","instance_id":"<init value>","nonce":"<init value>","request_id":"query_1","type":"data.query","query_ref":"q_loss"}
```

响应是type=response及frames/truncated，或type=error和error.code。frames只包含声明字段；宿主负责带账号凭据查询。数据尚未就绪可能返回data_unavailable，可在有限重试预算内稍后请求；不要无限重试或发送任意QuerySpec。

当前支持data.query和100–800px的有界panel.resize，宿主可能进一步夹紧高度；selection.emit返回unsupported。桥接消息有限额、去重和频率限制，单次响应不超过64KiB。展示的最大值只代表收到的投影/采样点，不自动表示全历史最佳。

inline HTML受64KiB源代码预算约束，artifact渲染另有256KiB上限。发布内容需要html:publish，改变数据能力需要html:bind_data，二者都不替代Dashboard/项目权限。

[正式契约](../reference/server/docs/api-contract.md) · [面板 schema](../schemas/dashboard.schema.json) · [文件存储](../reference/server/docs/storage.md)

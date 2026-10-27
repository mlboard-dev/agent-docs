# 当前基线的已知问题

基线：server `4caeb73`，2026-10-27文档示例HTTP验收。

## Step降采样的Relative字段

写入带elapsed_seconds的10条标量后，Step/min_max降采样查询返回的elapsed_seconds列为null；相同数据使用raw查询保留真实训练耗时。X坐标和标量值正常。

消费端必须保留缺失值，不补造Relative，也不能仅凭这条降采样响应断言训练没有记录耗时。需要真实Relative时，按预算读取raw结果核对；不要把所有查询无条件切到raw。本仓库只记录当前产品限制，没有修改服务端实现。

此项在scripts/verify_examples.py中明确记录为known_limitations，报告状态为passed_with_known_limitations；其他模板、preview/apply、MCP和HTML受限响应分别验证。

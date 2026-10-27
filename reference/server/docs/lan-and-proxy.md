> 来源：[server/docs/lan-and-proxy.md](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/docs/lan-and-proxy.md) · `73643d8`。链接已整理；勘误及示例泛化见[来源说明](../../../SOURCES.md)。部署行为以目标实例的 capabilities / registry / schemas 为准。

# 局域网与反向代理

应用监听地址和浏览器公开地址分别配置。直接以 LAN IP 访问的 Compose 示例：

```dotenv
MLBOARD_BIND_ADDRESS=192.168.1.10
MLBOARD_PORT=18896
MLBOARD_PUBLIC_URL=http://192.168.1.10:18896
MLBOARD_TRUSTED_PROXIES=
```

沿用原部署项目名执行 `docker compose --env-file deploy/.env -f deploy/compose.local.yml up -d`。单个实例采用一个 canonical 公开 origin；默认 strict Host 校验、浏览器 Origin、OAuth 回调和浏览器会话均以 `MLBOARD_PUBLIC_URL` 为准。LAN 地址不会自动开放注册，首次初始化后仍需账号／项目权限。

## SDK / Agent 的宽松 Host 模式

当同一个实例同时通过 LAN IP、容器名或额外代理地址调用，且收到 `403 untrusted_host`，可在服务端设置：

```dotenv
MLBOARD_HOST_VALIDATION=relaxed
```

二进制对应 `--host-validation relaxed`；默认 `strict`，未知值拒绝启动。Docker run 添加 `-e MLBOARD_HOST_VALIDATION=relaxed`。Compose 将此变量写入现有 `.env` 后，沿用原项目名和数据卷执行 `docker compose --env-file deploy/.env -f deploy/compose.local.yml up -d --force-recreate`。仅 restart 不会替换容器环境变量。

宽松模式接受格式合法的 Host 别名，后续仍需有效 Bearer key 和真实项目权限。它不会放宽浏览器 Origin/CSRF，不改变 OAuth 回调、分享链接、Secure cookie 或可信代理规则。浏览器仍从配置的 `MLBOARD_PUBLIC_URL` 登录；SDK/MCP 使用自己的访问地址及 Bearer key，通常不发送 Origin。如果前置反代也按域名过滤，还需让它把相应入口转发到这个实例。

## 反代到域名根路径

先配置域名与 TLS，再将 `MLBOARD_PUBLIC_URL` 改为最终 HTTPS origin（例如 `https://board.example.com`），应用只监听 loopback 或私有容器网络。HTTPS public URL 会自动启用 Secure cookie。API、Web 静态资源、SSE、WebSocket、分享链接和文件下载均保持原路径；当前不支持把整个应用挂在 `/mlboard/` 子路径。

- [Caddy 样本](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/deploy/reverse-proxy/Caddyfile.example)：自动 TLS、即时 SSE flush，原生转发 WebSocket。
- [Nginx 样本](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/deploy/reverse-proxy/nginx.conf.example)：保留原 Host，显式 Upgrade、关闭响应缓冲与代理缓存。上传上限可按应用与部署预算调整，不能只改代理绕过应用限制。

`MLBOARD_TRUSTED_PROXIES` 仅控制客户端 IP 的 `X-Forwarded-For` 信任；不会让任意 `X-Forwarded-Host`／`X-Forwarded-Proto` 覆盖 public URL。只填写实际代理的单个 IP/CIDR，例如 loopback 代理 `127.0.0.1/32,::1/128`，不要填写所有网段。代理覆盖外部传入的转发头；若还有上一层负载均衡，应明确每一跳的信任边界。不要把 Origin 校验去掉来修复部署地址不匹配。

验收包含：带 Origin 的登录与写入、会话 cookie、页面资源、SSE 首事件及时到达、WebSocket 101 升级、上传和 Range 下载；另检验 strict 模式拒绝别名 Host、relaxed 模式允许别名但无凭据仍401，两种模式均拒绝错误浏览器 Origin。strict 健康检查需要发送配置的 Host。

正式样本给上游响应等待设置 20 分钟的有限上限：Nginx `proxy_read_timeout 1200s`，Caddy transport 的 `response_header_timeout 20m` / `read_timeout 20m`。该余量覆盖数据工作上限 600 秒、分享预览复核上限 120 秒、默认输出 60 秒及 JSON 接收/调度；应用仍执行自身更严格的预算。Nginx 的默认读取间隔为 60 秒，会提前截断高上限查询；Caddy 未配置这些 transport 项时默认没有此上游响应等待限制，当前 demo 生成配置也没有额外的 60 秒限制。代理的读取间隔/响应头等待不等于应用的整次工作期限。若另外调整上传总时限、输出预算或有 CDN/负载均衡器，需一并核对其独立限制；SSE/WS 不设置整体 20 分钟生命周期。

实现依据：[Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)、[Nginx proxy 模块](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)。域名/TLS 证书没有配置时，不能把 LAN HTTP 验收描述为已经完成公网 HTTPS 验收。

## 开发机常驻 demo

本项目开发机使用独立的 `demo-live/` 目录、账号、数据、容器网络及 LAN 端口，和压测实例分开。具体运行地址、版本与验证证据记录在工作区工作历史中，运行凭据不进仓库。

demo 启动器读取专属 `settings.json` 的 `host_validation`（缺省 strict），写入应用容器环境并记录部署状态；只改变此设置也会重新部署。恢复中断发布时，核验待发布容器记录的模式，避免用后来改变的设置误判已有候选。

[LAN demo workflow](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/.github/workflows/demo.yml) 只在私有 `mlboard-dev/server` 的 `main` push 或手动触发时运行，使用该仓库专属 `mlboard-demo-x86` runner。checkout token 仅有 `contents: read`，不持久化。部署密钥受组织策略禁止时无需放宽策略，也无需在主机存储个人 PAT。

[部署脚本](https://github.com/mlboard-dev/server/blob/73643d862b4d6d930e6cfd41bb68acd949ed22df/deploy/demo/deploy.py) 先核对 commit、构建固定基础镜像并运行 Web/Go 检查，再短暂停止旧进程、完整复制数据库及附件到新数据目录。候选仅开放 loopback，在副本上迁移并检查登录／查询／流式接口后，才切换 Caddy 的 LAN 入口。候选失败时重启原进程，原数据库不受候选迁移影响。开始对外开放新数据库后，不自动恢复旧数据库丢弃已确认写入；持久化发布日志和定时 recovery 会继续完成新版本。

应用与代理由 Docker `restart: unless-stopped` 常驻。runner 的项目专用监督脚本通过 crontab 每两分钟确认进程与待恢复发布，机器重启后恢复；它不定时重新部署相同版本。构建／检查失败及剩余空间低于 8 GiB 时保留当前版本，错误保存在 `demo-live/logs/`。数据目录及 `credentials.json` 为私有，密码变化后需同步更新该文件才能通过后续登录验收。此服务是开发预览，不把生产数据导入演示实例。

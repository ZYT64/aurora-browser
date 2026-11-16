# free-model-router — 开发线免费模型自动路由器

17 车道（13 个不同模型，旗舰 ≥8），全部免费池。监听 127.0.0.1:18970，OpenAI 兼容。
- 模型名：`free-pool`（全车道）/ `free-fast`（跳过慢车道）
- 策略：lkgp（粘住上次成功车道）+ 自动 failover + 连续 3 失败冷却 5 分钟 + 90s 健康探测
- 接入方式：base_url=http://127.0.0.1:18970/v1，model=free-pool，无鉴权（仅本机）

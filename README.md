# Shadowrocket 规则

本项目基于
[Johnshall/Shadowrocket-ADBlock-Rules-Forever](https://github.com/Johnshall/Shadowrocket-ADBlock-Rules-Forever)
每日生成的规则，构建包含个人分流与广告过滤需求的 Shadowrocket 配置。

本地规则始终位于上游规则之前，当前包括：

- `jpn`、`nf` 和 `hk` 节点域名及 IP 直连，防止代理回环
- 阿尔比恩 Online 独立规则集与可手动选择节点的 `Albion` 策略组
- YouTube 响应处理与 QUIC 阻断
- 红果短剧广告域名与响应处理
- 喜马拉雅启动广告过滤
- 常用国际服务、AI 服务、GitHub 和 Telegram 分流

## 阿尔比恩分流

阿尔比恩规则单独存放在
[`rules/albion.list`](rules/albion.list)，覆盖官方域名以及游戏常用端口。
更新配置后，在 Shadowrocket 的 `Albion` 策略组中选择
`HK-Hysteria2` 即可。其他代理流量仍使用原有 `PROXY` 策略，不会自动使用
该节点。

## 自动更新

`.github/workflows/update-rules.yml` 每天北京时间 08:30 自动运行，也支持手动
触发。任务会下载上游 `sr_top500_whitelist_ad.conf`，检查文件结构、规则数量、
最终策略和本地必需规则，再合并 `custom/` 下的配置片段，生成：

- `hrd201-sr.conf`
- `hrd201-sr-v2.conf`
- `clash/johnshall-reject.yaml`
- `clash/johnshall-direct.yaml`
- `clash/johnshall-proxy.yaml`

如果上游文件不完整、规则数量异常、最终策略错误或本地必需规则缺失，构建会
直接失败并保留现有可用配置。

需要调整自定义配置时，应修改 `custom/` 和 `rules/` 下的源文件，不要直接编辑
自动生成的 `.conf` 文件。

## 订阅地址

```text
https://raw.githubusercontent.com/hrd201/shadowrocket-rules/main/hrd201-sr.conf
```

## 许可证

生成配置包含 Johnshall 项目的规则内容，按照 CC BY-SA 4.0 许可证分发。详情见
[LICENSE](LICENSE) 和 [NOTICE](NOTICE)。

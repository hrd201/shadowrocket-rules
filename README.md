# Shadowrocket Rules

This repository builds a customized Shadowrocket configuration from the daily
output of [Johnshall/Shadowrocket-ADBlock-Rules-Forever](https://github.com/Johnshall/Shadowrocket-ADBlock-Rules-Forever).

The generated configuration keeps these local rules ahead of the upstream base:

- direct routing for the `jpn` and `nf` proxy endpoints
- direct routing for the `hk` endpoint to prevent proxy loops
- a standalone Albion Online rule set with a selectable `Albion` policy group
- YouTube response processing and QUIC blocking
- Red Fruit ad-domain and response handling
- Ximalaya startup-ad filtering
- explicit routing for commonly used international, AI, GitHub, and Telegram services

## Update Process

`.github/workflows/update-rules.yml` runs daily at 08:30 Asia/Shanghai and can
also be started manually. It downloads the upstream
`sr_top500_whitelist_ad.conf`, validates its structure and minimum rule count,
prepends the files in `custom/`, and writes both `hrd201-sr.conf` and
`hrd201-sr-v2.conf`.

The build fails without replacing the existing configuration if the upstream
file is missing expected sections, contains an unexpected final policy, is too
small, or loses any required local marker.

The same build converts the upstream Shadowrocket policies into three Clash
classical providers under `clash/`: `johnshall-reject.yaml`,
`johnshall-direct.yaml`, and `johnshall-proxy.yaml`. Policy fields are removed
from provider entries, while `FINAL` and nested `RULE-SET` entries are excluded.

Edit the files under `custom/` instead of editing generated `.conf` files.

## Subscription

```text
https://raw.githubusercontent.com/hrd201/shadowrocket-rules/main/hrd201-sr.conf
```

## License

The generated configuration incorporates work from Johnshall's project and is
distributed under CC BY-SA 4.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

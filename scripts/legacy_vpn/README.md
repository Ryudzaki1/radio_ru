# Legacy VPN scripts

These scripts are archived from the early VPS/VPN experiments: Xray, VLESS,
VMess, Shadowsocks, OpenVPN, one-off TLS setup, and the old `/opt/ai-chill-radio`
deployment path.

They are not part of the current radio architecture.

Current production architecture:

- Russia/Yandex node: `/opt/radio_ru`, public website, admin panel, `/stream`.
- Europe node: WireGuard peer, private Caddy proxies for ElevenLabs and Telegram,
  and the EU Telegram bot when SSH access is available.
- Active operational scripts live in `scripts/`, `russia/scripts/`, and
  `europe/scripts/` outside this legacy folder.

Do not run scripts in this directory against production unless you intentionally
want to restore old VPN behavior.

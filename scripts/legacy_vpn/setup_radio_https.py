import os

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
DOMAIN = os.environ.get("RADIO_DOMAIN", "80-240-16-151.sslip.io")
REMOTE_DIR = os.environ.get("REMOTE_DIR", "/opt/ai-chill-radio")


SCRIPT = f"""
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

systemctl stop xray || true
systemctl disable xray || true

apt-get update
apt-get install -y caddy

cd {REMOTE_DIR}
if grep -q '^PORT=' .env; then
  sed -i 's#^PORT=.*#PORT=127.0.0.1:3000#' .env
else
  printf '\\nPORT=127.0.0.1:3000\\n' >> .env
fi
if grep -q '^PUBLIC_RADIO_URL=' .env; then
  sed -i 's#^PUBLIC_RADIO_URL=.*#PUBLIC_RADIO_URL=https://{DOMAIN}#' .env
else
  printf '\\nPUBLIC_RADIO_URL=https://{DOMAIN}\\n' >> .env
fi

docker compose up -d

cat > /etc/caddy/Caddyfile <<'EOF'
{DOMAIN} {{
    encode gzip zstd
    reverse_proxy 127.0.0.1:3000
}}
EOF

ufw allow 80/tcp || true
ufw allow 443/tcp || true

systemctl enable caddy
systemctl restart caddy
sleep 5
systemctl is-active caddy
docker ps --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'
curl -k -I --max-time 15 https://{DOMAIN}/ || true
journalctl -u caddy -n 80 --no-pager || true
"""


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    HOST,
    username=USER,
    password=PASSWORD,
    look_for_keys=False,
    allow_agent=False,
)

try:
    stdin, stdout, stderr = client.exec_command("bash -s", timeout=900)
    stdin.write(SCRIPT)
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out.encode("ascii", errors="replace").decode("ascii"))
    if err:
        print(err.encode("ascii", errors="replace").decode("ascii"))
    code = stdout.channel.recv_exit_status()
    if code:
        raise SystemExit(code)
finally:
    client.close()

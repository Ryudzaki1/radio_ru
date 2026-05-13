import os
import shlex

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
WG_PORT = os.environ.get("WG_PORT", "443")
CLIENT_NAME = os.environ.get("WG_CLIENT", "phone")


SCRIPT = r"""
set -euo pipefail
WG_DIR=/etc/wireguard
cd "$WG_DIR"

sed -i -E "s/^ListenPort = .*/ListenPort = ${WG_PORT}/" wg0.conf
sed -i -E "s/^Endpoint = ([^:]+):[0-9]+/Endpoint = \1:${WG_PORT}/" "${CLIENT_NAME}.conf"

ufw allow "${WG_PORT}/udp"
systemctl restart wg-quick@wg0
systemctl is-active wg-quick@wg0
wg show
echo "CLIENT_CONFIG_BEGIN"
cat "${CLIENT_NAME}.conf"
echo "CLIENT_CONFIG_END"
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
    command = (
        f"WG_PORT={shlex.quote(WG_PORT)} "
        f"CLIENT_NAME={shlex.quote(CLIENT_NAME)} "
        "bash -s"
    )
    stdin, stdout, stderr = client.exec_command(command, timeout=300)
    stdin.write(SCRIPT)
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out)
    if err:
        print(err.encode("ascii", errors="replace").decode("ascii"))
    code = stdout.channel.recv_exit_status()
    if code:
        raise SystemExit(code)
finally:
    client.close()

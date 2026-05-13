import os
import shlex

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
WG_PORT = os.environ.get("WG_PORT", "51820")
CLIENT_NAME = os.environ.get("WG_CLIENT", "phone")


SCRIPT = r"""
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y wireguard iptables resolvconf

SERVER_IFACE=$(ip -o -4 route show to default | awk '{print $5; exit}')
SERVER_IP=$(curl -4 -fsSL --max-time 10 https://api.ipify.org)
WG_DIR=/etc/wireguard
mkdir -p "$WG_DIR"
chmod 700 "$WG_DIR"
cd "$WG_DIR"

umask 077
wg genkey | tee server_private.key | wg pubkey > server_public.key
wg genkey | tee client_private.key | wg pubkey > client_public.key

SERVER_PRIVATE=$(cat server_private.key)
SERVER_PUBLIC=$(cat server_public.key)
CLIENT_PRIVATE=$(cat client_private.key)
CLIENT_PUBLIC=$(cat client_public.key)

cat > wg0.conf <<EOF
[Interface]
Address = 10.8.0.1/24
ListenPort = __WG_PORT__
PrivateKey = ${SERVER_PRIVATE}
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o ${SERVER_IFACE} -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o ${SERVER_IFACE} -j MASQUERADE

[Peer]
PublicKey = ${CLIENT_PUBLIC}
AllowedIPs = 10.8.0.2/32
EOF

sed -i "s/__WG_PORT__/$WG_PORT/g" wg0.conf

cat > ${CLIENT_NAME}.conf <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIVATE}
Address = 10.8.0.2/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = ${SERVER_PUBLIC}
Endpoint = ${SERVER_IP}:$WG_PORT
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

sysctl -w net.ipv4.ip_forward=1
printf 'net.ipv4.ip_forward=1\n' > /etc/sysctl.d/99-wireguard-forward.conf

ufw allow ${WG_PORT}/udp
systemctl enable wg-quick@wg0
systemctl restart wg-quick@wg0
systemctl is-active wg-quick@wg0
echo "SERVER_IP=${SERVER_IP}"
echo "SERVER_IFACE=${SERVER_IFACE}"
echo "CLIENT_CONFIG_BEGIN"
cat ${CLIENT_NAME}.conf
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
    stdin, stdout, stderr = client.exec_command(command, timeout=900)
    stdin.write(SCRIPT)
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(out)
    if err:
        print(err)
    if code:
        raise SystemExit(code)
finally:
    client.close()

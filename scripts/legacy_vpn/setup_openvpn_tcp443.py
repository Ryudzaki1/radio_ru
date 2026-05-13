import os
import shlex

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
CLIENT_NAME = os.environ.get("OVPN_CLIENT", "phone")


SCRIPT = r"""
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y openvpn easy-rsa iptables

systemctl stop xray || true
systemctl disable xray || true

SERVER_IFACE=$(ip -o -4 route show to default | awk '{print $5; exit}')
SERVER_IP=$(curl -4 -fsSL --max-time 10 https://api.ipify.org)
PKI_DIR=/etc/openvpn/pki-build
OUT_DIR=/etc/openvpn/client
mkdir -p "$OUT_DIR"

rm -rf "$PKI_DIR"
make-cadir "$PKI_DIR"
cd "$PKI_DIR"

cat > vars <<'EOF'
set_var EASYRSA_BATCH "1"
set_var EASYRSA_ALGO "ec"
set_var EASYRSA_DIGEST "sha256"
EOF

./easyrsa init-pki
./easyrsa build-ca nopass
./easyrsa build-server-full server nopass
./easyrsa build-client-full "${CLIENT_NAME}" nopass
openvpn --genkey secret ta.key

cp pki/ca.crt /etc/openvpn/server/ca.crt
cp pki/issued/server.crt /etc/openvpn/server/server.crt
cp pki/private/server.key /etc/openvpn/server/server.key
cp ta.key /etc/openvpn/server/ta.key

cat > /etc/openvpn/server/server.conf <<EOF
port 443
proto tcp-server
dev tun
topology subnet
server 10.9.0.0 255.255.255.0
ifconfig-pool-persist /var/log/openvpn/ipp.txt
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 1.1.1.1"
push "dhcp-option DNS 8.8.8.8"
keepalive 10 120
cipher AES-256-GCM
data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305
auth SHA256
tls-server
dh none
tls-auth ta.key 0
ca ca.crt
cert server.crt
key server.key
user nobody
group nogroup
persist-key
persist-tun
verb 3
EOF

sysctl -w net.ipv4.ip_forward=1
printf 'net.ipv4.ip_forward=1\n' > /etc/sysctl.d/99-vpn-forward.conf

iptables -C FORWARD -i tun0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -i tun0 -j ACCEPT
iptables -C FORWARD -o tun0 -j ACCEPT 2>/dev/null || iptables -A FORWARD -o tun0 -j ACCEPT
iptables -t nat -C POSTROUTING -s 10.9.0.0/24 -o "${SERVER_IFACE}" -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -s 10.9.0.0/24 -o "${SERVER_IFACE}" -j MASQUERADE

ufw allow 443/tcp

systemctl enable openvpn-server@server
systemctl restart openvpn-server@server
systemctl is-active openvpn-server@server

CLIENT_FILE="${OUT_DIR}/${CLIENT_NAME}.ovpn"
cat > "$CLIENT_FILE" <<EOF
client
dev tun
proto tcp-client
remote ${SERVER_IP} 443
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305
auth SHA256
verb 3
key-direction 1
<ca>
$(cat pki/ca.crt)
</ca>
<cert>
$(awk '/BEGIN/,/END/' "pki/issued/${CLIENT_NAME}.crt")
</cert>
<key>
$(cat "pki/private/${CLIENT_NAME}.key")
</key>
<tls-auth>
$(cat ta.key)
</tls-auth>
EOF

echo "SERVER_IP=${SERVER_IP}"
echo "SERVER_IFACE=${SERVER_IFACE}"
echo "CLIENT_CONFIG_BEGIN"
cat "$CLIENT_FILE"
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
    command = f"CLIENT_NAME={shlex.quote(CLIENT_NAME)} bash -s"
    stdin, stdout, stderr = client.exec_command(command, timeout=900)
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

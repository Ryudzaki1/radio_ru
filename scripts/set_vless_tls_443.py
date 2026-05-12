import json
import os

import paramiko


HOST = os.environ["VPS_HOST"]
DOMAIN = os.environ["VPN_DOMAIN"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
CONFIG_PATH = "/usr/local/etc/xray/config.json"
CERT_DIR = f"/etc/ssl/xray/{DOMAIN}"
CERT_PATH = f"{CERT_DIR}/fullchain.pem"
KEY_PATH = f"{CERT_DIR}/privkey.pem"


def run(client, command, timeout=600):
    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if code:
        raise RuntimeError(f"{command}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    return out.strip()


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, allow_agent=False)

try:
    run(client, "export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y socat openssl ca-certificates curl", timeout=900)
    run(client, "systemctl stop xray")
    run(client, "mkdir -p /root/.acme.sh")
    run(client, "curl -fsSL https://get.acme.sh | sh -s email=admin@" + DOMAIN, timeout=900)
    run(client, f"~/.acme.sh/acme.sh --set-default-ca --server letsencrypt", timeout=300)
    run(client, f"~/.acme.sh/acme.sh --issue --standalone -d {DOMAIN} --keylength ec-256 --force", timeout=900)
    run(client, f"mkdir -p {CERT_DIR}")
    run(
        client,
        f"~/.acme.sh/acme.sh --install-cert -d {DOMAIN} --ecc "
        f"--fullchain-file {CERT_PATH} --key-file {KEY_PATH} "
        "--reloadcmd 'systemctl restart xray'",
        timeout=300,
    )

    uuid = run(client, "xray uuid")
    sftp = client.open_sftp()
    with sftp.file(CONFIG_PATH, "r") as fh:
        old_config = json.loads(fh.read().decode("utf-8"))

    outbounds = old_config.get("outbounds") or [{"protocol": "freedom", "tag": "direct"}]
    config = {
        "log": {"loglevel": "info"},
        "inbounds": [
            {
                "tag": "vless-tls-443",
                "listen": "0.0.0.0",
                "port": 443,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": uuid, "email": "phone-vless-tls"}],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "tls",
                    "tlsSettings": {
                        "serverName": DOMAIN,
                        "minVersion": "1.2",
                        "certificates": [
                            {
                                "certificateFile": CERT_PATH,
                                "keyFile": KEY_PATH,
                            }
                        ],
                    },
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"],
                },
            }
        ],
        "outbounds": outbounds,
    }

    with sftp.file(CONFIG_PATH, "w") as fh:
        fh.write(json.dumps(config, indent=2))
    sftp.close()

    run(client, "ufw allow 443/tcp")
    test = run(client, "xray run -test -config /usr/local/etc/xray/config.json")
    run(client, "systemctl enable xray && systemctl restart xray")
    status = run(client, "systemctl is-active xray")
    listen = run(client, "ss -lntp | grep ':443 ' || true")
    link = f"vless://{uuid}@{DOMAIN}:443?encryption=none&type=tcp&security=tls&sni={DOMAIN}&fp=chrome#{DOMAIN}-vless-tls"

    print("TEST=" + test.splitlines()[-1])
    print("XRAY_STATUS=" + status)
    print("LISTEN=" + listen.replace("\n", " | "))
    print("VLESS_LINK=" + link)
finally:
    client.close()

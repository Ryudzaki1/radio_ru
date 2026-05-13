import os
import re
import sys
import time

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]


def run(client, command, timeout=300):
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if code != 0:
        raise RuntimeError(f"Command failed ({code}): {command}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    return out.strip()


def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST,
        username=USER,
        password=PASSWORD,
        look_for_keys=False,
        allow_agent=False,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
    )

    try:
        run(client, "export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y curl unzip openssl ca-certificates", timeout=600)
        run(client, "bash -c \"$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)\" @ install", timeout=600)

        uuid = run(client, "xray uuid")
        keys = run(client, "xray x25519")
        private_match = re.search(r"Private\s*[Kk]ey:\s*(\S+)", keys)
        public_match = re.search(r"(?:Public\s*[Kk]ey|Password \(PublicKey\)):\s*(\S+)", keys)
        if not private_match or not public_match:
            raise RuntimeError(f"Could not parse xray x25519 output:\n{keys}")
        private_key = private_match.group(1)
        public_key = public_match.group(1)
        short_id = run(client, "openssl rand -hex 8")

        config = f"""\
{{
  "log": {{
    "loglevel": "warning"
  }},
  "inbounds": [
    {{
      "tag": "vless-reality",
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {{
        "clients": [
          {{
            "id": "{uuid}",
            "flow": "xtls-rprx-vision",
            "email": "phone"
          }}
        ],
        "decryption": "none"
      }},
      "streamSettings": {{
        "network": "tcp",
        "security": "reality",
        "realitySettings": {{
          "show": false,
          "dest": "www.microsoft.com:443",
          "xver": 0,
          "serverNames": [
            "www.microsoft.com"
          ],
          "privateKey": "{private_key}",
          "shortIds": [
            "{short_id}"
          ]
        }}
      }},
      "sniffing": {{
        "enabled": true,
        "destOverride": [
          "http",
          "tls",
          "quic"
        ]
      }}
    }}
  ],
  "outbounds": [
    {{
      "protocol": "freedom",
      "tag": "direct"
    }},
    {{
      "protocol": "blackhole",
      "tag": "blocked"
    }}
  ]
}}
"""

        sftp = client.open_sftp()
        with sftp.file("/usr/local/etc/xray/config.json", "w") as f:
            f.write(config)
        sftp.close()

        run(client, "systemctl enable xray && systemctl restart xray")
        time.sleep(2)
        status = run(client, "systemctl is-active xray")
        listen = run(client, "ss -lntp | grep ':443 ' || true")

        link = (
            f"vless://{uuid}@{HOST}:443"
            f"?type=tcp&security=reality&pbk={public_key}&fp=chrome"
            f"&sni=www.microsoft.com&sid={short_id}&flow=xtls-rprx-vision"
            f"#{HOST}-vless-reality"
        )

        print("XRAY_STATUS=" + status)
        print("LISTEN=" + listen.replace("\n", " | "))
        print("UUID=" + uuid)
        print("PUBLIC_KEY=" + public_key)
        print("SHORT_ID=" + short_id)
        print("VLESS_LINK=" + link)
    finally:
        client.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

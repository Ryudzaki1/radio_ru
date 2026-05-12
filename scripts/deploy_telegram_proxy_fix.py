import os
import time

import paramiko


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RU_HOST = os.environ["RU_HOST"]
RU_USER = os.environ.get("RU_USER", "radio")
RU_KEY = os.environ["RU_KEY"]
EU_HOST = os.environ["EU_HOST"]
EU_USER = os.environ.get("EU_USER", "root")
EU_PASS = os.environ["EU_PASS"]


def load_key(path):
    for key_cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return key_cls.from_private_key_file(path)
        except paramiko.SSHException:
            continue
    raise RuntimeError("Could not read SSH key")


def connect_key(host, user, key_path):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, pkey=load_key(key_path), look_for_keys=False, allow_agent=False)
    return client


def connect_password(host, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, look_for_keys=False, allow_agent=False)
    return client


def run(client, command, stdin_data=None, timeout=900):
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    if stdin_data is not None:
        stdin.write(stdin_data)
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out.encode("ascii", errors="replace").decode("ascii"))
    if err:
        print(err.encode("ascii", errors="replace").decode("ascii"))
    if code:
        raise RuntimeError(f"remote command failed with code {code}: {command}")
    return out


def read_local(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as handle:
        return handle.read()


def sudo_write(client, path, content):
    run(client, f"sudo -n tee {path} >/dev/null", stdin_data=content, timeout=120)


def deploy_eu(client):
    print("=== EU proxy ===")
    sudo_write(client, "/etc/caddy/Caddyfile", read_local("europe/Caddyfile"))
    run(client, "\n".join([
        "set -euo pipefail",
        "ufw allow in on wg0 to any port 18080 proto tcp || true",
        "ufw allow in on wg0 to any port 18081 proto tcp || true",
        "caddy validate --config /etc/caddy/Caddyfile",
        "systemctl restart caddy",
        "systemctl is-active caddy",
        "curl -sS -o /dev/null -w 'telegram_proxy_http=%{http_code}\\n' --max-time 10 http://10.77.0.1:18081/",
        "ss -lntup | grep -E ':(18080|18081) ' || true",
    ]), timeout=180)


def deploy_ru(client):
    print("=== RU app ===")
    sudo_write(client, "/opt/radio_ru/bot/bot.js", read_local("bot/bot.js"))
    sudo_write(client, "/opt/radio_ru/docker-compose.yml", read_local("docker-compose.yml"))
    run(client, "\n".join([
        "set -euo pipefail",
        "cd /opt/radio_ru",
        "sudo -n chown radio:radio bot/bot.js docker-compose.yml || true",
        "if grep -q '^TELEGRAM_API_BASE_URL=' .env; then",
        "  sed -i 's#^TELEGRAM_API_BASE_URL=.*#TELEGRAM_API_BASE_URL=http://10.77.0.1:18081#' .env",
        "else",
        "  printf '\\nTELEGRAM_API_BASE_URL=http://10.77.0.1:18081\\n' >> .env",
        "fi",
        "curl -sS --max-time 15 -o /tmp/telegram_getme.json -w 'telegram_getme_http=%{http_code}\\n' \"http://10.77.0.1:18081/bot$(grep '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2-)/getMe\" || true",
        "python3 - <<'PY'",
        "import json",
        "try:",
        "    data = json.load(open('/tmp/telegram_getme.json', encoding='utf-8'))",
        "    result = data.get('result') or {}",
        "    print('telegram_getme_ok=' + str(data.get('ok')))",
        "    print('telegram_bot_username=' + str(result.get('username', '')))",
        "except Exception as exc:",
        "    print('telegram_getme_parse_error=' + str(exc))",
        "PY",
        "sudo -n docker compose up -d --build --force-recreate",
        "sudo -n docker exec ai-chill-radio-bot sh -lc 'rm -f /cache/config/bot-link.json' || true",
        "sudo -n docker restart ai-chill-radio-bot >/dev/null",
    ]), timeout=1800)
    time.sleep(12)
    run(client, "\n".join([
        "set -euo pipefail",
        "cd /opt/radio_ru",
        "echo '--- containers'",
        "sudo -n docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'",
        "echo '--- public checks'",
        "curl -sS -I --max-time 10 http://127.0.0.1/admin.html | head -5",
        "curl -sS --max-time 8 -o /tmp/stream.bin -w 'stream_http=%{http_code} stream_size=%{size_download} stream_type=%{content_type}\\n' http://127.0.0.1/stream || true",
        "echo '--- bot link state'",
        "sudo -n docker exec ai-chill-radio-bot sh -lc 'cat /cache/config/bot-link.json 2>/dev/null || true'",
        "echo '--- recent bot errors'",
        "sudo -n docker logs --since 20s ai-chill-radio-bot 2>&1 | grep -Ei 'error|failed|timeout' || true",
    ]), timeout=240)


ru = connect_key(RU_HOST, RU_USER, RU_KEY)
eu = connect_password(EU_HOST, EU_USER, EU_PASS)
try:
    deploy_eu(eu)
    deploy_ru(ru)
finally:
    ru.close()
    eu.close()

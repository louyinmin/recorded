#!/bin/bash

# 续费雷达 Microsoft OAuth2 邮件配置助手
# 用法:
#   ./setup_expiry_microsoft_oauth2.sh
#   ./setup_expiry_microsoft_oauth2.sh --callback-url 'http://localhost:53682/callback?code=...'
#   ./setup_expiry_microsoft_oauth2.sh --callback-url 'http://localhost:53682/callback?code=...' --test

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="$APP_DIR/data.db"
USERNAME="lou"
TENANT_ID=""
CLIENT_ID=""
CLIENT_SECRET=""
REDIRECT_URI="http://localhost:53682/callback"
CALLBACK_URL=""
AUTH_CODE=""
RUN_TEST="0"

print_help() {
  cat <<EOF
用法:
  ./setup_expiry_microsoft_oauth2.sh [选项]

不传 --callback-url / --code 时，只打印管理员同意 URL 和授权 URL。
传入 --callback-url 或 --code 时，会兑换 refresh_token 并写入续费雷达数据库。

选项:
  --username <name>          续费雷达账号名（默认: lou）
  --tenant-id <id>           Microsoft 租户 ID（不传则读取已保存值）
  --client-id <id>           Azure App Client ID（不传则读取已保存值）
  --client-secret <secret>   Azure App Client Secret（不传则读取已保存值）
  --redirect-uri <uri>       回调地址（默认: http://localhost:53682/callback）
  --callback-url <url>       授权成功后浏览器地址栏里的完整回调 URL
  --code <code>              授权回调里的 code，和 --callback-url 二选一
  --test                     写入后立即发送一封测试邮件
  --db-path <path>           指定数据库路径（默认: \$APP_DIR/data.db）
  -h, --help                 显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --username)
      USERNAME="${2:-}"
      shift 2
      ;;
    --tenant-id)
      TENANT_ID="${2:-}"
      shift 2
      ;;
    --client-id)
      CLIENT_ID="${2:-}"
      shift 2
      ;;
    --client-secret)
      CLIENT_SECRET="${2:-}"
      shift 2
      ;;
    --redirect-uri)
      REDIRECT_URI="${2:-}"
      shift 2
      ;;
    --callback-url)
      CALLBACK_URL="${2:-}"
      shift 2
      ;;
    --code)
      AUTH_CODE="${2:-}"
      shift 2
      ;;
    --test)
      RUN_TEST="1"
      shift
      ;;
    --db-path)
      DB_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "未知参数: $1"
      print_help
      exit 1
      ;;
  esac
done

if [[ ! -f "$DB_PATH" ]]; then
  echo "错误: 数据库文件不存在: $DB_PATH"
  exit 1
fi

if [[ -x "$APP_DIR/venv/bin/python3" ]]; then
  PYTHON_BIN="$APP_DIR/venv/bin/python3"
elif [[ -x "$APP_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$APP_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

cd "$APP_DIR"

"$PYTHON_BIN" - <<PY
import json
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request

from expiry_backend.reminder import send_email
from expiry_backend.security import decrypt_secret, encrypt_secret, ensure_app_secret
from expiry_backend.service import (
    EMAIL_AUTH_MICROSOFT_OAUTH2,
    MICROSOFT_OAUTH_SCOPE,
    get_email_delivery_auth,
    row_to_dict,
    utcnow_iso,
)

db_path = r"""$DB_PATH"""
base_dir = r"""$APP_DIR"""
username = r"""$USERNAME"""
tenant_id_arg = r"""$TENANT_ID""".strip()
client_id_arg = r"""$CLIENT_ID""".strip()
client_secret_arg = r"""$CLIENT_SECRET""".strip()
redirect_uri = r"""$REDIRECT_URI""".strip()
callback_url = r"""$CALLBACK_URL""".strip()
auth_code = r"""$AUTH_CODE""".strip()
run_test = r"""$RUN_TEST""" == "1"

if not redirect_uri:
    raise SystemExit("错误: redirect_uri 不能为空")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
try:
    user = conn.execute(
        "SELECT id, email FROM expiry_users WHERE username=?",
        (username,),
    ).fetchone()
    if not user:
        raise SystemExit(f"错误: 用户不存在: {username}")

    settings_row = conn.execute(
        "SELECT * FROM expiry_email_settings WHERE user_id=?",
        (user["id"],),
    ).fetchone()
    if not settings_row:
        raise SystemExit(f"错误: 邮件配置不存在: {username}")
    settings = row_to_dict(settings_row)

    app_secret, _ = ensure_app_secret(base_dir)
    tenant_id = tenant_id_arg or str(settings.get("oauth_tenant_id") or "").strip()
    client_id = client_id_arg or str(settings.get("oauth_client_id") or "").strip()
    client_secret = client_secret_arg or decrypt_secret(settings.get("oauth_client_secret_encrypted", ""), app_secret)

    if not tenant_id or not client_id:
        raise SystemExit("错误: 请先提供 tenant_id 和 client_id，或在页面中保存这两项")
    if not client_secret:
        raise SystemExit("错误: 请先提供 client_secret，或在页面中保存 Client Secret")

    admin_consent_params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    })
    auth_params = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": MICROSOFT_OAUTH_SCOPE,
        "prompt": "consent",
    })
    print("管理员同意 URL:")
    print(f"https://login.microsoftonline.com/{tenant_id}/adminconsent?{admin_consent_params}")
    print("")
    print("授权 URL:")
    print(f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?{auth_params}")

    if callback_url and not auth_code:
        parsed = urllib.parse.urlparse(callback_url)
        query = urllib.parse.parse_qs(parsed.query)
        auth_code = (query.get("code") or [""])[0].strip()
    if not auth_code:
        print("")
        print("尚未传入回调 code。请先打开上面的管理员同意 URL，再打开授权 URL，最后把完整回调地址用 --callback-url 传回来。")
        raise SystemExit(0)

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": MICROSOFT_OAUTH_SCOPE,
    }).encode("utf-8")
    request = urllib.request.Request(
        token_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            token_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
            message = parsed.get("error_description") or parsed.get("error") or body
        except Exception:
            message = body
        raise SystemExit(f"错误: 授权 code 兑换失败: {message}")

    token_data = json.loads(token_body)
    refresh_token = str(token_data.get("refresh_token") or "").strip()
    access_token = str(token_data.get("access_token") or "").strip()
    if not refresh_token:
        raise SystemExit("错误: Microsoft 响应缺少 refresh_token，请确认授权 URL 包含 offline_access")
    if not access_token:
        raise SystemExit("错误: Microsoft 响应缺少 access_token")

    conn.execute(
        """
        UPDATE expiry_email_settings
        SET auth_mode=?, oauth_tenant_id=?, oauth_client_id=?, oauth_client_secret_encrypted=?,
            oauth_refresh_token_encrypted=?, oauth_access_token_encrypted='', oauth_access_token_expires_at='',
            updated_at=?
        WHERE user_id=?
        """,
        (
            EMAIL_AUTH_MICROSOFT_OAUTH2,
            tenant_id,
            client_id,
            encrypt_secret(client_secret, app_secret),
            encrypt_secret(refresh_token, app_secret),
            utcnow_iso(),
            user["id"],
        ),
    )
    conn.commit()
    print("")
    print("完成: refresh_token 已写入数据库。")

    if run_test:
        recipient = str(user["email"] or "").strip()
        if not recipient:
            raise SystemExit("错误: 用户资料中没有接收邮箱，无法发送测试邮件")
        fresh_settings = row_to_dict(conn.execute(
            "SELECT * FROM expiry_email_settings WHERE user_id=?",
            (user["id"],),
        ).fetchone())
        auth_payload = get_email_delivery_auth(conn, fresh_settings, base_dir)
        send_email(
            fresh_settings,
            auth_payload.get("smtp_password", ""),
            recipient,
            "【续费雷达】测试邮件",
            "这是一封来自续费雷达的测试邮件，用于验证你的 Microsoft OAuth2 邮件配置。",
            auth_mode=auth_payload.get("auth_mode", "password"),
            oauth_access_token=auth_payload.get("oauth_access_token", ""),
        )
        print(f"完成: 测试邮件已发送到 {recipient}")
finally:
    conn.close()
PY

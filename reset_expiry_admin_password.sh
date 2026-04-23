#!/bin/bash

# 续费雷达管理员密码重置脚本
# 用法:
#   ./reset_expiry_admin_password.sh
#   ./reset_expiry_admin_password.sh --password 'Init@2026'
#   ./reset_expiry_admin_password.sh --username 'lou' --must-change 1

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="$APP_DIR/data.db"
USERNAME="lou"
PASSWORD=""
MUST_CHANGE="1"

print_help() {
  cat <<EOF
用法:
  ./reset_expiry_admin_password.sh [选项]

选项:
  --username <name>       要重置的账号名（默认: lou）
  --password <password>   指定新密码（不传则自动生成随机密码）
  --must-change <0|1>     登录后是否强制改密（默认: 1）
  --db-path <path>        指定数据库路径（默认: \$APP_DIR/data.db）
  -h, --help              显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --username)
      USERNAME="${2:-}"
      shift 2
      ;;
    --password)
      PASSWORD="${2:-}"
      shift 2
      ;;
    --must-change)
      MUST_CHANGE="${2:-}"
      shift 2
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

if [[ "$MUST_CHANGE" != "0" && "$MUST_CHANGE" != "1" ]]; then
  echo "错误: --must-change 只能是 0 或 1"
  exit 1
fi

if [[ -z "$USERNAME" ]]; then
  echo "错误: 用户名不能为空"
  exit 1
fi

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

if [[ -z "$PASSWORD" ]]; then
  PASSWORD="$("$PYTHON_BIN" - <<'PY'
import secrets
print(secrets.token_urlsafe(12))
PY
)"
fi

cd "$APP_DIR"

"$PYTHON_BIN" - <<PY
import sqlite3
from expiry_backend.service import (
    DEFAULT_NOTIFY_OFFSETS,
    DEFAULT_TIMEZONE,
    ROLE_ADMIN,
    STATUS_ACTIVE,
    gen_id,
    hash_password,
    utcnow_iso,
)

db_path = r"""$DB_PATH"""
username = r"""$USERNAME"""
password = r"""$PASSWORD"""
must_change = int(r"""$MUST_CHANGE""")

conn = sqlite3.connect(db_path)
created = False
try:
    row = conn.execute(
        "SELECT id FROM expiry_users WHERE username=?",
        (username,),
    ).fetchone()
    if not row:
        user_id = gen_id()
        now = utcnow_iso()
        conn.execute(
            """
            INSERT INTO expiry_users (
                id, username, password_hash, role, status, email, must_change_password, created_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                username,
                hash_password(password),
                ROLE_ADMIN,
                STATUS_ACTIVE,
                "",
                must_change,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO expiry_user_settings (user_id, default_notify_offsets, timezone, updated_at)
            VALUES (?,?,?,?)
            """,
            (user_id, DEFAULT_NOTIFY_OFFSETS, DEFAULT_TIMEZONE, now),
        )
        conn.execute(
            """
            INSERT INTO expiry_email_settings (
                user_id, smtp_host, smtp_port, smtp_username, smtp_password_encrypted,
                smtp_security, from_email, from_name, enabled, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (user_id, "", 587, "", "", "starttls", "", "", 0, now),
        )
        cur = None
        created = True
    else:
        cur = conn.execute(
            "UPDATE expiry_users SET password_hash=?, must_change_password=? WHERE username=?",
            (hash_password(password), must_change, username),
        )
    conn.commit()
finally:
    conn.close()

print(f"账号: {username}")
print(f"临时密码: {password}")
print(f"must_change_password: {must_change}")
if created:
    print("created_admin: 1")
else:
    print("created_admin: 0")
    print(f"updated_rows: {cur.rowcount}")
PY
if [[ $? -eq 0 ]]; then
  echo "完成: 管理员账号已就绪，密码已更新。"
fi

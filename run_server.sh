#!/bin/bash

# Recorded 双模块系统 - 一键部署脚本（Ubuntu 22）
# 用法: sudo ./run_server.sh

set -e

# ===== 配置 =====
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
FLASK_PORT=5000
NGINX_SITE_NAME="travel-recorder"
CRON_FILE="/etc/cron.d/recorded-expiry-reminder"

echo "=============================="
echo "  Recorded 双模块 - 部署脚本"
echo "=============================="
echo ""
echo "项目目录: $APP_DIR"
echo ""

# ===== 1. 安装系统依赖 =====
echo "[1/7] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx > /dev/null 2>&1
echo "  ✅ python3, pip, nginx 已安装"

# ===== 2. 创建虚拟环境并安装 Python 依赖 =====
echo "[2/7] 安装 Python 依赖..."
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
echo "  ✅ Flask 已安装"

# ===== 3. 初始化数据库 =====
echo "[3/7] 初始化数据库..."
cd "$APP_DIR"
"$APP_DIR/venv/bin/python3" -c "from app import init_db; init_db()"
echo "  ✅ 数据库已初始化"

ADMIN_INFO=$("$APP_DIR/venv/bin/python3" <<PY
from expiry_backend.service import ensure_initial_admin
info = ensure_initial_admin(r"$APP_DIR/data.db", r"$APP_DIR", username="lou")
print(info["username"])
print(info["password"] or "")
print("created" if info["created"] else "existing")
PY
)
EXPIRY_ADMIN_USER="$(echo "$ADMIN_INFO" | sed -n '1p')"
EXPIRY_ADMIN_PASSWORD="$(echo "$ADMIN_INFO" | sed -n '2p')"
EXPIRY_ADMIN_STATUS="$(echo "$ADMIN_INFO" | sed -n '3p')"
echo "  ✅ 续费雷达管理员已检查"

# ===== 4. 配置 Nginx =====
echo "[4/7] 配置 Nginx..."
# 替换 nginx.conf 中的路径为实际路径
sed "s|/home/user/recorded|$APP_DIR|g" "$APP_DIR/nginx.conf" > "/etc/nginx/sites-available/$NGINX_SITE_NAME"
# 启用站点
ln -sf "/etc/nginx/sites-available/$NGINX_SITE_NAME" "/etc/nginx/sites-enabled/$NGINX_SITE_NAME"
# 移除默认站点（避免冲突）
rm -f /etc/nginx/sites-enabled/default
# 测试配置
nginx -t
echo "  ✅ Nginx 配置完成"

# ===== 5. 安装续费提醒任务 =====
echo "[5/7] 安装续费提醒定时任务..."
chmod +x "$APP_DIR/run_expiry_reminder.sh"
cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CRON_TZ=Asia/Shanghai
0 9 * * * root cd $APP_DIR && RECORDED_BASE_DIR=$APP_DIR RECORDED_DB_PATH=$APP_DIR/data.db $APP_DIR/run_expiry_reminder.sh >> $APP_DIR/expiry_reminder.log 2>&1
EOF
chmod 644 "$CRON_FILE"
echo "  ✅ 每天 09:00 的提醒扫描已配置"

# ===== 6. 启动 Flask 后端 =====
echo "[6/7] 启动 Flask 后端..."
# 先停止已有的 Flask 进程
pkill -f "python3.*app.py" 2>/dev/null || true
sleep 1
cd "$APP_DIR"
nohup "$APP_DIR/venv/bin/python3" "$APP_DIR/app.py" > "$APP_DIR/flask.log" 2>&1 &
FLASK_PID=$!
echo "  ✅ Flask 后端已启动 (PID: $FLASK_PID, 端口: $FLASK_PORT)"

# ===== 7. 重启 Nginx =====
echo "[7/7] 重启 Nginx..."
systemctl restart nginx
systemctl enable nginx
if command -v systemctl &> /dev/null; then
    systemctl restart cron 2>/dev/null || systemctl restart crond 2>/dev/null || true
fi
echo "  ✅ Nginx 已启动"

echo ""
echo "=============================="
echo "  部署完成！"
echo "=============================="
echo ""
SERVER_IP="$(hostname -I | awk '{print $1}')"
echo "旅行记账: http://$SERVER_IP/login.html"
echo "续费雷达: http://$SERVER_IP/expiry/login.html"
echo ""
echo "续费雷达管理员: $EXPIRY_ADMIN_USER"
if [ "$EXPIRY_ADMIN_STATUS" = "created" ]; then
    echo "续费雷达初始密码: $EXPIRY_ADMIN_PASSWORD"
else
    echo "续费雷达初始密码: 已存在管理员账号，本次未重置"
fi
echo "旅行记账登录: 使用续费雷达账号体系"
echo ""
echo "Flask 日志: $APP_DIR/flask.log"
echo "提醒日志: $APP_DIR/expiry_reminder.log"
echo "停止 Flask: kill $FLASK_PID"
echo "停止 Nginx: sudo systemctl stop nginx"
echo ""

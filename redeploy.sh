#!/bin/bash

# Recorded 双模块系统 - 一键重新部署脚本
# 用法: sudo ./redeploy.sh

set -e

# ===== 配置 =====
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
FLASK_PORT=5000
NGINX_SITE_NAME="travel-recorder"
CRON_FILE="/etc/cron.d/recorded-expiry-reminder"

echo "=============================="
echo "  Recorded 双模块 - 重新部署"
echo "=============================="
echo ""
echo "项目目录: $APP_DIR"
echo ""

# ===== 1. 停止现有服务 =====
echo "[1/4] 停止现有服务..."
pkill -f "python3.*app.py" 2>/dev/null || true
echo "  ✅ Flask 进程已停止"

# ===== 2. 安装/更新 Python 依赖 =====
echo "[2/4] 更新 Python 依赖..."
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
echo "  ✅ 依赖已更新"

# ===== 3. 启动 Flask 后端 =====
echo "[3/5] 检查数据库与提醒任务..."
cd "$APP_DIR"
"$APP_DIR/venv/bin/python3" -c "from app import init_db; init_db()"
"$APP_DIR/venv/bin/python3" <<PY
from expiry_backend.service import ensure_initial_admin
ensure_initial_admin(r"$APP_DIR/data.db", r"$APP_DIR", username="lou")
PY
chmod +x "$APP_DIR/run_expiry_reminder.sh"
cat > "$CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CRON_TZ=Asia/Shanghai
0 9 * * * root cd $APP_DIR && RECORDED_BASE_DIR=$APP_DIR RECORDED_DB_PATH=$APP_DIR/data.db $APP_DIR/run_expiry_reminder.sh >> $APP_DIR/expiry_reminder.log 2>&1
EOF
chmod 644 "$CRON_FILE"
echo "  ✅ 数据库与提醒任务已就绪"

# ===== 4. 启动 Flask 后端 =====
echo "[4/5] 启动 Flask 后端..."
cd "$APP_DIR"
nohup "$APP_DIR/venv/bin/python3" "$APP_DIR/app.py" > "$APP_DIR/flask.log" 2>&1 &
FLASK_PID=$!
sleep 2
# 检查进程是否存活
if kill -0 $FLASK_PID 2>/dev/null; then
    echo "  ✅ Flask 后端已启动 (PID: $FLASK_PID, 端口: $FLASK_PORT)"
else
    echo "  ❌ Flask 启动失败，请查看日志: $APP_DIR/flask.log"
    exit 1
fi

# ===== 5. 重启 Nginx（如果已安装）=====
echo "[5/5] 重启 Nginx..."
if command -v systemctl &> /dev/null && systemctl is-active --quiet nginx 2>/dev/null; then
    systemctl restart nginx
    systemctl restart cron 2>/dev/null || systemctl restart crond 2>/dev/null || true
    echo "  ✅ Nginx 已重启"
else
    echo "  ⚠️  Nginx 未安装或未运行，跳过"
fi

echo ""
echo "=============================="
echo "  重新部署完成！"
echo "=============================="
echo ""

# 获取服务器IP
if command -v hostname &> /dev/null; then
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -n "$SERVER_IP" ]; then
        echo "访问地址: http://$SERVER_IP/login.html"
        echo "续费雷达: http://$SERVER_IP/expiry/login.html"
    else
        echo "访问地址: http://localhost:$FLASK_PORT/login.html"
        echo "续费雷达: http://localhost:$FLASK_PORT/expiry/login.html"
    fi
else
    echo "访问地址: http://localhost:$FLASK_PORT/login.html"
    echo "续费雷达: http://localhost:$FLASK_PORT/expiry/login.html"
fi

echo ""
echo "登录账号: lou"
echo "登录密码: 123 (如已修改则使用新密码)"
echo ""
echo "Flask 日志: tail -f $APP_DIR/flask.log"
echo "提醒日志: tail -f $APP_DIR/expiry_reminder.log"
echo "停止服务: pkill -f 'python3.*app.py'"
echo ""

#!/bin/bash

# 旅游记账系统 - 一键重新部署脚本
# 用法: sudo ./redeploy.sh

set -e

# ===== 配置 =====
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
FLASK_PORT=5000
NGINX_SITE_NAME="travel-recorder"

echo "=============================="
echo "  旅游记账系统 - 重新部署"
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
echo "[3/4] 启动 Flask 后端..."
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

# ===== 4. 重启 Nginx（如果已安装）=====
echo "[4/4] 重启 Nginx..."
if command -v systemctl &> /dev/null && systemctl is-active --quiet nginx 2>/dev/null; then
    systemctl restart nginx
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
    else
        echo "访问地址: http://localhost:$FLASK_PORT/login.html"
    fi
else
    echo "访问地址: http://localhost:$FLASK_PORT/login.html"
fi

echo ""
echo "登录账号: lou"
echo "登录密码: 123 (如已修改则使用新密码)"
echo ""
echo "Flask 日志: tail -f $APP_DIR/flask.log"
echo "停止服务: pkill -f 'python3.*app.py'"
echo ""
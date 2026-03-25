#!/bin/bash

# 旅游记账系统 - 一键部署脚本（Ubuntu 22）
# 用法: sudo ./run_server.sh

set -e

# ===== 配置 =====
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
FLASK_PORT=5000
NGINX_SITE_NAME="travel-recorder"

echo "=============================="
echo "  旅游记账系统 - 部署脚本"
echo "=============================="
echo ""
echo "项目目录: $APP_DIR"
echo ""

# ===== 1. 安装系统依赖 =====
echo "[1/6] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx > /dev/null 2>&1
echo "  ✅ python3, pip, nginx 已安装"

# ===== 2. 创建虚拟环境并安装 Python 依赖 =====
echo "[2/6] 安装 Python 依赖..."
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
echo "  ✅ Flask 已安装"

# ===== 3. 初始化数据库 =====
echo "[3/6] 初始化数据库..."
cd "$APP_DIR"
"$APP_DIR/venv/bin/python3" -c "from app import init_db; init_db()"
echo "  ✅ 数据库已初始化"

# ===== 4. 配置 Nginx =====
echo "[4/6] 配置 Nginx..."
# 替换 nginx.conf 中的路径为实际路径
sed "s|/home/user/recorded|$APP_DIR|g" "$APP_DIR/nginx.conf" > "/etc/nginx/sites-available/$NGINX_SITE_NAME"
# 启用站点
ln -sf "/etc/nginx/sites-available/$NGINX_SITE_NAME" "/etc/nginx/sites-enabled/$NGINX_SITE_NAME"
# 移除默认站点（避免冲突）
rm -f /etc/nginx/sites-enabled/default
# 测试配置
nginx -t
echo "  ✅ Nginx 配置完成"

# ===== 5. 启动 Flask 后端 =====
echo "[5/6] 启动 Flask 后端..."
# 先停止已有的 Flask 进程
pkill -f "python3.*app.py" 2>/dev/null || true
sleep 1
cd "$APP_DIR"
nohup "$APP_DIR/venv/bin/python3" "$APP_DIR/app.py" > "$APP_DIR/flask.log" 2>&1 &
FLASK_PID=$!
echo "  ✅ Flask 后端已启动 (PID: $FLASK_PID, 端口: $FLASK_PORT)"

# ===== 6. 重启 Nginx =====
echo "[6/6] 重启 Nginx..."
systemctl restart nginx
systemctl enable nginx
echo "  ✅ Nginx 已启动"

echo ""
echo "=============================="
echo "  部署完成！"
echo "=============================="
echo ""
echo "访问地址: http://$(hostname -I | awk '{print $1}')/login.html"
echo "登录账号: lou"
echo "登录密码: 123"
echo ""
echo "Flask 日志: $APP_DIR/flask.log"
echo "停止 Flask: kill $FLASK_PID"
echo "停止 Nginx: sudo systemctl stop nginx"
echo ""

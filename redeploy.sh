#!/bin/bash

# Recorded 双模块系统 - 一键重新部署脚本
# 用法: sudo ./redeploy.sh

set -e

# ===== 配置 =====
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
FLASK_PORT=5000
NGINX_SITE_NAME="travel-recorder"
CRON_FILE="/etc/cron.d/recorded-expiry-reminder"
WECHAT_ENV_FILE="${WECHAT_ENV_FILE:-/etc/recorded/wechat-miniprogram.env}"
NBAGAME_ASSET_SPECS_TEMPLATE="$APP_DIR/projects/nbagame_api/config/assets.json"

echo "=============================="
echo "  Recorded 双模块 - 重新部署"
echo "=============================="
echo ""
echo "项目目录: $APP_DIR"
echo ""

# ===== 0. 加载服务器本地密钥配置 =====
echo "[0/6] 加载微信小程序环境变量..."
if [ ! -f "$WECHAT_ENV_FILE" ]; then
    echo "  ❌ 缺少微信小程序环境变量文件: $WECHAT_ENV_FILE"
    echo "  请先创建该文件，并写入 NBA、Timing 和 NBAGAME 的微信凭据。"
    exit 1
fi

set -a
# shellcheck disable=SC1090
. "$WECHAT_ENV_FILE"
set +a

for name in \
    WECHAT_MINIPROGRAM_NBA_APPID \
    WECHAT_MINIPROGRAM_NBA_SECRET \
    WECHAT_MINIPROGRAM_TIMING_APPID \
    WECHAT_MINIPROGRAM_TIMING_SECRET \
    NBAGAME_WECHAT_APPID \
    NBAGAME_WECHAT_SECRET \
    NBAGAME_TOKEN_SECRET \
    NBAGAME_PUBLIC_BASE_URL
do
    if [ -z "${!name:-}" ]; then
        echo "  ❌ $WECHAT_ENV_FILE 缺少: $name"
        exit 1
    fi
done

NBAGAME_ASSET_SPECS_FILE="${NBAGAME_ASSET_SPECS_FILE:-/etc/recorded/nbagame-assets.json}"
export NBAGAME_ASSET_SPECS_FILE
if [ ! -f "$NBAGAME_ASSET_SPECS_FILE" ]; then
    install -d -m 755 "$(dirname "$NBAGAME_ASSET_SPECS_FILE")"
    install -m 644 "$NBAGAME_ASSET_SPECS_TEMPLATE" "$NBAGAME_ASSET_SPECS_FILE"
    echo "  ✅ 已初始化 nbagame 图片白名单: $NBAGAME_ASSET_SPECS_FILE"
else
    echo "  ✅ 使用服务器 nbagame 图片白名单: $NBAGAME_ASSET_SPECS_FILE"
fi
if ! python3 -m json.tool "$NBAGAME_ASSET_SPECS_FILE" >/dev/null; then
    echo "  ❌ nbagame 图片白名单不是有效 JSON: $NBAGAME_ASSET_SPECS_FILE"
    exit 1
fi
echo "  ✅ 微信小程序环境变量已加载"

# ===== 1. 安装/更新 Python 依赖 =====
echo "[1/6] 更新 Python 依赖..."
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
echo "  ✅ 依赖已更新"

# ===== 2. Validate nbagame assets before stopping the running service =====
echo "[2/6] 检查 nbagame 图片配置..."
NBAGAME_ASSETS_DIR="${NBAGAME_ASSETS_DIR:-$APP_DIR/nbagame}"
export NBAGAME_ASSETS_DIR
cd "$APP_DIR"
"$APP_DIR/venv/bin/python3" -c \
    "import os; from pathlib import Path; from nbagame_backend.service import load_asset_specs, snapshot_local_assets; snapshot_local_assets(Path(os.environ['NBAGAME_ASSETS_DIR']).resolve(), load_asset_specs(os.environ['NBAGAME_ASSET_SPECS_FILE']))"
echo "  ✅ nbagame 图片配置与文件完整"

# ===== 3. 停止现有服务 =====
echo "[3/6] 停止现有服务..."
pkill -f "python3.*app.py" 2>/dev/null || true
echo "  ✅ Flask 进程已停止"

# ===== 4. 检查数据库与提醒任务 =====
echo "[4/6] 检查数据库与提醒任务..."
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

# ===== 5. 启动 Flask 后端 =====
echo "[5/6] 启动 Flask 后端..."
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

# ===== 6. 重启 Nginx（如果已安装）=====
echo "[6/6] 重启 Nginx..."
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
echo "登录说明: 旅行记账与续费雷达共用续费雷达账号体系"
echo ""
echo "Flask 日志: tail -f $APP_DIR/flask.log"
echo "提醒日志: tail -f $APP_DIR/expiry_reminder.log"
echo "停止服务: pkill -f 'python3.*app.py'"
echo ""

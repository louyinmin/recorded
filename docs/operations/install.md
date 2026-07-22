# Recorded 多模块系统 - 安装与运行指南

## 项目简介

这是一个基于 **Flask + SQLite + Nginx** 的多模块系统：

- **旅游记账**：记录旅行支出
- **续费雷达**：管理订阅、会员和到期提醒
- **NBA 球员数据**：采集新浪 NBA 球员资料并为微信小程序提供 JSON 接口

各模块共享服务器资源与部署体系，但账号、页面、API 和业务数据完全隔离。

## 环境要求

- **操作系统**：Ubuntu 22.04 LTS
- **必备组件**：
  - Python 3（Ubuntu 22 默认已安装）
  - python3-pip
  - python3-venv
  - Nginx

## 目录结构

```
recorded/
├── app.py                         # Flask entrypoint and compatibility routes
├── home.html                      # Unified browser entry page
├── projects/
│   ├── life_atlas/                # Life Atlas frontend, backend, docs
│   ├── travel_accounting/         # Travel Accounting frontend and docs
│   ├── expiry_radar/              # Expiry Radar frontend, backend, docs
│   ├── nba_api/                   # NBA Mini Program backend and docs
│   ├── timing_api/                # Timing Mini Program backend and docs
│   └── shared/                    # Shared frontend assets and WeChat backend
├── docs/
│   ├── architecture/              # Cross-project architecture notes
│   └── operations/                # Deployment and Git operation notes
├── expiry_backend/                # Compatibility package entry
├── life_backend/                  # Compatibility package entry
├── nba_backend/                   # Compatibility package entry
├── timing_backend/                # Compatibility package entry
├── wechat_backend/                # Compatibility package entry
├── requirements.txt               # Python dependencies
├── nginx.conf                     # Nginx config template
├── run_server.sh                  # One-shot deployment script
├── run_expiry_reminder.sh         # Expiry reminder job runner
├── reset_expiry_admin_password.sh # Expiry Radar admin password reset
├── data.db                        # Travel and Expiry SQLite database, generated at runtime
├── life.db                        # Life Atlas SQLite database, generated at runtime
├── nba.db                         # NBA SQLite database, generated at runtime
└── wechat.db                      # WeChat session SQLite database, generated at runtime
```

## 一键部署（推荐）

### 1. 将项目上传到服务器

```bash
scp -r recorded/ user@your-server:/home/user/
```

### 2. 赋予脚本执行权限并运行

```bash
cd /home/user/recorded
chmod +x run_server.sh
sudo ./run_server.sh
```

脚本会自动完成以下操作：
1. 安装 Python3、pip、venv、Nginx
2. 创建 Python 虚拟环境并安装 Flask
3. 初始化旅游记账、续费雷达、人生记录、NBA 球员与微信小程序用户数据表
4. 创建续费雷达管理员账号与应用密钥
5. 配置 Nginx（静态文件 + 反向代理）
6. 安装续费提醒定时任务
7. 启动 Flask 后端并重启 Nginx

### 3. 访问系统

部署完成后，在浏览器中访问：

```text
http://服务器IP/login.html
http://服务器IP/expiry/login.html
```

- 续费雷达管理员：`lou`
- 续费雷达初始密码：首次部署时在终端打印一次
- 旅行记账登录：使用续费雷达账号体系

## 手动部署

如果一键脚本不适用，可按以下步骤手动操作：

### 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx
```

### 2. 安装 Python 依赖

```bash
cd /home/user/recorded
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 3. 初始化并启动 Flask

```bash
cd /home/user/recorded
./venv/bin/python3 -c "from app import init_db; init_db()"
./venv/bin/python3 - <<'PY'
from expiry_backend.service import ensure_initial_admin
info = ensure_initial_admin('/home/user/recorded/data.db', '/home/user/recorded', username='lou')
print(info)
PY
nohup ./venv/bin/python3 app.py > flask.log 2>&1 &
```

Flask 默认监听 `127.0.0.1:5000`。

### 4. NBA 球员数据接口

NBA 数据默认写入项目目录下的 `nba.db`，可用 `NBA_DB_PATH` 指定独立路径。球星卡图片默认读取项目目录下的 `nba_images`，可用 `NBA_IMAGE_DIR` 指定独立路径；球员头像默认读取项目目录下的 `nba_avatar`，可用 `NBA_AVATAR_DIR` 指定独立路径；球队图标默认读取项目目录下的 `nba_team_images`，可用 `NBA_TEAM_IMAGE_DIR` 指定独立路径。小程序读取接口：

```text
GET /api/nba/players
GET /api/nba/players?team=洛杉矶湖人&position=后卫
GET /api/nba/players/search?q=Luke
GET /api/nba/filters
GET /api/nba/players/:pid
GET /api/nba/images/:filename
GET /api/nba/images/missing
GET /api/nba/avatars/:filename
GET /api/nba/avatars/missing
GET /api/nba/team-images/:filename
GET /api/nba/team-images/missing
```

采集接口访问新浪 NBA。生产环境建议设置 `NBA_SYNC_TOKEN`，调用时通过 `X-NBA-Sync-Token` 请求头传递：

```text
POST /api/nba/sync/player
POST /api/nba/sync/images
POST /api/nba/sync/avatars
POST /api/nba/sync/team-images
POST /api/nba/sync/rookies-2026
POST /api/nba/sync
```

### 5. 微信小程序登录接口

微信会话数据默认写入项目目录下的 `wechat.db`，可用 `WECHAT_DB_PATH` 指定独立路径。小程序登录接口：

```text
POST /api/nba/wechat/session
POST /api/timing/wechat/session
POST /api/wechat/session
```

请求体：

```json
{
  "code": "wx.login 返回的临时代码",
  "app": "nba"
}
```

项目命名路由会自动选择对应小程序密钥；通用 `/api/wechat/session` 必须显式传 `app`，否则后端无法判断应使用哪一组 AppID/AppSecret。

服务端通过微信 `jscode2session` 换取 `openid`，查找或创建本地用户，返回：

```json
{
  "userId": "wx_xxx",
  "openid": "wechat_openid",
  "app": "nba",
  "sessionToken": "opaque_backend_session_token",
  "expiresAt": "2026-07-19T00:00:00"
}
```

微信配置同步接口通过 `Authorization: Bearer <sessionToken>` 识别当前用户：

```text
GET /api/nba/user-config
PATCH /api/nba/user-config
GET /api/nba/players/batch?pids=player_pid_1,player_pid_2
GET /api/timing/plan-config
PUT /api/timing/plan-config
PATCH /api/timing/plan-config/default-task-duration
POST /api/timing/plan-config/custom-plans
PUT /api/timing/plan-config/custom-plans/:planId
DELETE /api/timing/plan-config/custom-plans/:planId
GET /api/timing/task-config
PUT /api/timing/task-config
POST /api/timing/task-config/tasks
PUT /api/timing/task-config/tasks/:taskId
DELETE /api/timing/task-config/tasks/:taskId
GET /api/timing/stats?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
PUT /api/timing/stats/:date
DELETE /api/timing/stats?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
```

NBA 用户配置请求和响应中的 `config` 结构：

```json
{
  "associated_home_player_pid": ["player_pid_1", "player_pid_2"],
  "current_home_player_pid": "player_pid_2",
  "search_default_player_pid": ["player_pid_3"]
}
```

`GET /api/nba/user-config` also returns additive `homeCards` metadata for the NBA Mini Program home cache:

```json
{
  "homeCards": {
    "pids": ["player_pid_1", "player_pid_2"],
    "currentPid": "player_pid_2",
    "currentCardId": "player_pid_2_2024_base",
    "cardSelection": {
      "player_pid_1": "player_pid_1_2024_base",
      "player_pid_2": "player_pid_2_2024_base"
    },
    "configUpdatedAt": "2026-06-19T00:00:00",
    "playersUpdatedAt": "2026-06-20T08:30:00",
    "cardsUpdatedAt": "2026-06-20T08:30:00",
    "dataVersion": "home_8f3c0d9a1b2c"
  }
}
```

生产环境必须配置：

```bash
WECHAT_MINIPROGRAM_NBA_APPID=your-nba-appid
WECHAT_MINIPROGRAM_NBA_SECRET=your-nba-secret
WECHAT_MINIPROGRAM_TIMING_APPID=your-timing-appid
WECHAT_MINIPROGRAM_TIMING_SECRET=your-timing-secret
```

`redeploy.sh` 默认从服务器本地文件 `/etc/recorded/wechat-miniprogram.env` 读取这些变量。该文件只保存在服务器，不提交到 Git：

```bash
sudo install -d -m 700 /etc/recorded
sudo tee /etc/recorded/wechat-miniprogram.env >/dev/null <<'EOF'
WECHAT_MINIPROGRAM_NBA_APPID=your-nba-appid
WECHAT_MINIPROGRAM_NBA_SECRET=your-nba-secret
WECHAT_MINIPROGRAM_TIMING_APPID=your-timing-appid
WECHAT_MINIPROGRAM_TIMING_SECRET=your-timing-secret
EOF
sudo chmod 600 /etc/recorded/wechat-miniprogram.env
```

`WECHAT_MINIPROGRAM_*_APPID` 和 `WECHAT_MINIPROGRAM_*_SECRET` 只保存在服务器环境变量或部署平台密钥管理中，不提交到 Git，也不返回给小程序。配置好本地文件后，后续部署继续使用：

Court Deck uses its own database and credentials under `/nbagame/v1`. Add these values to the same server-side environment file. The first four are required by `redeploy.sh`; the remaining values pin production storage and application identity explicitly:

```bash
NBAGAME_DB_PATH=/var/lib/recorded/nbagame.db
NBAGAME_APP_ID=court-deck-prod
NBAGAME_ASSET_MANIFEST_VERSION=20260722.1
NBAGAME_WECHAT_APPID=your-court-deck-appid
NBAGAME_WECHAT_SECRET=your-court-deck-secret
NBAGAME_TOKEN_SECRET=replace-with-a-long-random-server-secret
NBAGAME_PUBLIC_BASE_URL=https://api.example.com
NBAGAME_PUBLISHED_ASSETS_DIR=/var/lib/recorded/nbagame-assets
NBAGAME_MAX_REQUEST_BYTES=2097152
NBAGAME_LOGIN_RATE_LIMIT=20
NBAGAME_LOGIN_RATE_WINDOW_SECONDS=60
```

Create the persistent database and asset directory before the first deployment:

```bash
sudo install -d -m 750 /var/lib/recorded /var/lib/recorded/nbagame-assets
```

The asset publisher reads a fixed whitelist from the repository's `nbagame/` directory and copies it into immutable version directories. Set `NBAGAME_ASSETS_DIR` only when the source directory differs. `NBAGAME_PUBLIC_BASE_URL` must be the HTTPS origin registered as a legal WeChat domain and must not include `/nbagame/v1`. See `projects/nbagame_api/docs/frontend-api.md` for the frontend contract.

```bash
sudo ./redeploy.sh
```

### 6. 配置 Nginx

```bash
# 编辑 nginx.conf 中的 root 路径为实际项目路径
# 然后复制到 nginx 配置目录
sudo cp nginx.conf /etc/nginx/sites-available/travel-recorder
sudo ln -sf /etc/nginx/sites-available/travel-recorder /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 7. 配置续费提醒任务

创建文件 `/etc/cron.d/recorded-expiry-reminder`：

```bash
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CRON_TZ=Asia/Shanghai
0 9 * * * root cd /home/user/recorded && RECORDED_BASE_DIR=/home/user/recorded RECORDED_DB_PATH=/home/user/recorded/data.db /home/user/recorded/run_expiry_reminder.sh >> /home/user/recorded/expiry_reminder.log 2>&1
```

### 7. 访问

```text
http://服务器IP/login.html
http://服务器IP/expiry/login.html
```

## 常见问题

### Q: 80 端口被占用？

编辑 `nginx.conf` 中的 `listen 80;` 改为其他端口（如 `listen 8080;`），然后重启 nginx：

```bash
sudo systemctl restart nginx
```

访问时使用 `http://服务器IP:8080/login.html`

### Q: Flask 进程如何管理？

```bash
# 查看进程
ps aux | grep app.py

# 停止
pkill -f "python3.*app.py"

# 重新启动
cd /home/user/recorded
nohup ./venv/bin/python3 app.py > flask.log 2>&1 &
```

### Q: 数据保存在哪里？

数据保存在服务器端的 `data.db` 文件（SQLite 数据库）中。  
两个模块共用这个文件，但使用不同的数据表。

### Q: 旅行记账现在用什么账号登录？

旅行记账不再使用固定账号。  
它与续费雷达共用 `expiry_users` 账号体系：

- 登录页仍然独立：`/login.html` 与 `/expiry/login.html`
- 账号管理统一在续费雷达管理员后台完成
- 旅行记账侧不提供改密入口，请在 `/expiry/settings.html` 修改密码
- 旅行、支付人、类别数据按账号隔离

### Q: 如何备份数据？

```bash
cp /home/user/recorded/data.db /home/user/recorded/data.db.backup
```

### Q: 如何查看 Flask 日志？

```bash
tail -f /home/user/recorded/flask.log
```

### Q: 如何查看续费提醒日志？

```bash
tail -f /home/user/recorded/expiry_reminder.log
```

### Q: 初始化已执行过，如何只重置续费雷达管理员密码？

```bash
cd /home/user/recorded
chmod +x reset_expiry_admin_password.sh

# 自动生成随机临时密码（默认强制首次登录改密）
./reset_expiry_admin_password.sh

# 或者手动指定密码
./reset_expiry_admin_password.sh --password 'Init@2026'
```

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
├── app.py                  # Flask 后端（API 服务）
├── expiry_backend/         # 到期管理后端模块
├── life_backend/           # 人生记录后端模块
├── nba_backend/            # NBA 球员数据后端模块
├── wechat_backend/         # 微信小程序登录会话后端模块
├── expiry/                 # 到期管理前端页面与静态资源
├── requirements.txt        # Python 依赖
├── nginx.conf              # Nginx 配置模板
├── run_server.sh           # 一键部署脚本
├── run_expiry_reminder.sh  # 到期提醒脚本
├── reset_expiry_admin_password.sh  # 重置续费雷达管理员密码
├── data.db                 # 旅游记账与续费雷达 SQLite 数据库（运行后自动生成）
├── life.db                 # 人生记录 SQLite 数据库（运行后自动生成）
├── nba.db                  # NBA 球员 SQLite 数据库（运行后自动生成）
├── wechat.db               # 微信小程序用户 SQLite 数据库（运行后自动生成）
├── login.html              # 登录页
├── trips.html              # 旅行列表页
├── trip.html               # 单次旅行记账页
├── INSTALL.md              # 本文档
├── recorded.md             # 需求说明（原始文档）
├── expiry.md               # 续费雷达说明
└── assets/
    ├── css/
    │   └── style.css       # 全局样式
    └── js/
        ├── common.js       # 公共工具函数 + API 封装
        ├── login.js        # 登录逻辑
        ├── trips.js        # 旅行列表逻辑
        └── trip.js         # 记账详情逻辑
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
GET /api/timing/plan-config
PUT /api/timing/plan-config
PATCH /api/timing/plan-config/default-task-duration
POST /api/timing/plan-config/custom-plans
PUT /api/timing/plan-config/custom-plans/:planId
DELETE /api/timing/plan-config/custom-plans/:planId
```

生产环境必须配置：

```bash
WECHAT_MINIPROGRAM_NBA_APPID=wxb329162424904f03
WECHAT_MINIPROGRAM_NBA_SECRET=your-nba-secret
WECHAT_MINIPROGRAM_TIMING_APPID=wxb57f6c567b4033fa
WECHAT_MINIPROGRAM_TIMING_SECRET=your-timing-secret
```

`WECHAT_MINIPROGRAM_*_SECRET` 只保存在服务器环境变量或部署平台密钥管理中，不提交到 Git，也不返回给小程序。

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

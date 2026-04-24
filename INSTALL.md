# Recorded 双模块系统 - 安装与运行指南

## 项目简介

这是一个基于 **Flask + SQLite + Nginx** 的双模块系统：

- **旅游记账**：记录旅行支出
- **续费雷达**：管理订阅、会员和到期提醒

两个模块共享服务器资源与部署体系，但账号、页面、API 和业务数据完全隔离。

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
├── expiry/                 # 到期管理前端页面与静态资源
├── requirements.txt        # Python 依赖
├── nginx.conf              # Nginx 配置模板
├── run_server.sh           # 一键部署脚本
├── run_expiry_reminder.sh  # 到期提醒脚本
├── reset_expiry_admin_password.sh  # 重置续费雷达管理员密码
├── data.db                 # SQLite 数据库（运行后自动生成）
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
3. 初始化旅游记账与续费雷达的数据表
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

### 4. 配置 Nginx

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

### 5. 配置续费提醒任务

创建文件 `/etc/cron.d/recorded-expiry-reminder`：

```bash
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CRON_TZ=Asia/Shanghai
0 9 * * * root cd /home/user/recorded && RECORDED_BASE_DIR=/home/user/recorded RECORDED_DB_PATH=/home/user/recorded/data.db /home/user/recorded/run_expiry_reminder.sh >> /home/user/recorded/expiry_reminder.log 2>&1
```

### 6. 访问

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

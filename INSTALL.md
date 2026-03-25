# 旅游记账系统 - 安装与运行指南

## 项目简介

这是一个旅游记账 H5 页面系统，适配微信浏览器及移动端打开。  
采用 **Flask + SQLite** 后端，数据存储在服务器端，多人可通过浏览器共同操作同一份数据。  
前端由 **Nginx** 托管静态文件，并反向代理 API 请求到 Flask。

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
├── requirements.txt        # Python 依赖
├── nginx.conf              # Nginx 配置模板
├── run_server.sh           # 一键部署脚本
├── data.db                 # SQLite 数据库（运行后自动生成）
├── login.html              # 登录页
├── trips.html              # 旅行列表页
├── trip.html               # 单次旅行记账页
├── INSTALL.md              # 本文档
├── recorded.md             # 需求说明（原始文档）
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
3. 初始化 SQLite 数据库
4. 配置 Nginx（静态文件 + 反向代理）
5. 启动 Flask 后端（后台运行）
6. 重启 Nginx

### 3. 访问系统

部署完成后，在浏览器中访问：

```
http://服务器IP/login.html
```

- 登录账号：`lou`
- 登录密码：`123`

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

### 5. 访问

```
http://服务器IP/login.html
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

数据保存在服务器端的 `data.db` 文件（SQLite 数据库）中。所有用户共享同一份数据。

### Q: 如何备份数据？

```bash
cp /home/user/recorded/data.db /home/user/recorded/data.db.backup
```

### Q: 如何查看 Flask 日志？

```bash
tail -f /home/user/recorded/flask.log
```

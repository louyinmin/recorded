# 续费雷达（到期管理 WEB）

## 产品定位

续费雷达是一个与原旅游记账完全独立的 WEB 模块，用来管理各类订阅、会员和一次性到期资源，例如：

- GPT 会员
- 机场会员
- 视频会员
- 域名 / 云服务
- 单次付费事项

它与旅行记账共享同一台服务器、同一个 Flask 进程、同一个 SQLite 文件与部署脚本，但账号、登录态、数据表、前端页面和 API 都独立隔离。

## 核心能力

- 独立账号登录
- 多账号独立数据
- 到期日管理
- 月度 / 年度预计支出统计
- 站内提醒
- 用户自配 SMTP 邮件提醒（支持 SMTP 密码 / Microsoft OAuth2）
- 管理员账号管理

## 页面入口

- `/expiry/login.html`
- `/expiry/dashboard.html`
- `/expiry/settings.html`
- `/expiry/admin-users.html`

## 技术落点

- 后端目录：`expiry_backend/`
- 前端目录：`expiry/`
- API 前缀：`/api/expiry/*`
- localStorage key：`expiry_token`
- 定时任务脚本：`run_expiry_reminder.sh`

## 初始化行为

首次部署会自动：

- 初始化到期管理数据表
- 生成 `.expiry_secret`
- 创建管理员账号 `lou`
- 打印一次初始密码
- 安装每天 `09:00` 的提醒任务

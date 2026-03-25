常用 Git 命令
# 查看状态
git status

# 添加修改的文件
git add .

# 提交
git commit -m "描述修改内容"

# 查看历史
git log --oneline

# 切换branch
git branch -M main


本地推送到远程仓库
# 添加远程仓库
git remote add origin https://github.com/louyinmin/recorded.git

# 推送到远程
git push -u origin main

# 增加邮箱配置
git config --global user.email "lymlym76@hotmail.com" 
git config --global user.name "louyinmin"


服务器同步代码

# 首次克隆
git clone https://github.com/louyinmin/recorded.git

# 后续更新
cd recorded
git pull
./redeploy.sh

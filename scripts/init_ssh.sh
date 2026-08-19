#!/bin/bash
# ============================================================
# 玄武固件扫描平台 - SSH 环境初始化脚本
# ============================================================
# 用途：在 PAI-DSW 环境中自动重建 SSH 软链接和 Git 配置
# 原因：/root/.ssh 软链接在环境重启后丢失，需每次会话初始化
# 用法：source /mnt/workspace/firmware_scanner/scripts/init_ssh.sh
# ============================================================

set -e

echo "🔐 初始化 SSH 环境..."

# 1. 检查持久化 SSH 目录是否存在
if [ ! -d "/mnt/workspace/.ssh" ]; then
    echo "⚠️  /mnt/workspace/.ssh 不存在，创建中..."
    mkdir -p /mnt/workspace/.ssh
    chmod 700 /mnt/workspace/.ssh
fi

# 2. 检查 /root/.ssh 软链接是否存在
if [ -L "/root/.ssh" ]; then
    # 软链接存在，检查是否指向正确位置
    target=$(readlink /root/.ssh)
    if [ "$target" = "/mnt/workspace/.ssh" ]; then
        echo "✅ /root/.ssh 软链接已存在且指向正确"
    else
        echo "⚠️  /root/.ssh 软链接指向错误：$target，修复中..."
        rm -f /root/.ssh
        ln -s /mnt/workspace/.ssh /root/.ssh
    fi
elif [ -d "/root/.ssh" ]; then
    # 是普通目录而非软链接，备份并替换
    echo "⚠️  /root/.ssh 是普通目录，迁移到持久化位置..."
    if [ -d "/root/.ssh.bak" ]; then
        rm -rf /root/.ssh.bak
    fi
    mv /root/.ssh /root/.ssh.bak
    ln -s /mnt/workspace/.ssh /root/.ssh
    echo "✅ 已迁移到 /mnt/workspace/.ssh，原目录备份到 /root/.ssh.bak"
else
    # 不存在，直接创建软链接
    echo "🔗 创建 /root/.ssh 软链接..."
    ln -s /mnt/workspace/.ssh /root/.ssh
fi

# 3. 验证 SSH 密钥
if [ -f "/mnt/workspace/.ssh/id_ed25519" ]; then
    echo "✅ SSH 私钥存在：/mnt/workspace/.ssh/id_ed25519"
else
    echo "⚠️  SSH 私钥不存在，需要重新生成并添加到 GitHub"
    echo "   执行：ssh-keygen -t ed25519 -C 'your_email@example.com'"
fi

# 4. 验证 known_hosts
if [ -f "/mnt/workspace/.ssh/known_hosts" ]; then
    echo "✅ known_hosts 存在"
else
    echo "⚠️  known_hosts 不存在，添加 GitHub 主机密钥..."
    ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> /mnt/workspace/.ssh/known_hosts 2>/dev/null
fi

# 5. 设置正确的权限
chmod 700 /mnt/workspace/.ssh 2>/dev/null || true
chmod 600 /mnt/workspace/.ssh/id_ed25519 2>/dev/null || true
chmod 644 /mnt/workspace/.ssh/id_ed25519.pub 2>/dev/null || true
chmod 644 /mnt/workspace/.ssh/known_hosts 2>/dev/null || true

# 6. 测试 SSH 连接
echo "🧪 测试 GitHub SSH 连接..."
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "✅ GitHub SSH 连接成功"
else
    echo "⚠️  GitHub SSH 连接失败，请检查密钥是否已添加到 GitHub"
    echo "   公钥位置：/mnt/workspace/.ssh/id_ed25519.pub"
fi

echo "✅ SSH 环境初始化完成"

# ============================================================
# 自动执行：在 .bashrc 中添加以下行以在每次登录时自动执行
# ============================================================
# if [ -f /mnt/workspace/firmware_scanner/scripts/init_ssh.sh ]; then
#     source /mnt/workspace/firmware_scanner/scripts/init_ssh.sh
# fi
# ============================================================

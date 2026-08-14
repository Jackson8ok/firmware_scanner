# Multi-stage Dockerfile for Firmware Scanner
# 优化镜像大小，提高安全性

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.10-slim AS builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# 下载 Grype 二进制文件
RUN wget -qO- https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin


# ============================================
# Stage 2: Production
# ============================================
FROM python:3.10-slim AS production

LABEL maintainer="玄武 Team <contact@pokeclaw.io>"
LABEL org.opencontainers.image.source="https://github.com/pokeclaw/scanner"
LABEL org.opencontainers.image.description="固件漏洞扫描平台 - R155 合规检查"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    binwalk \
    squashfs-tools \
    p7zip-full \
    libmagic1 \
    file \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从 builder 复制 wheels 并安装
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN groupadd -r scanner && useradd -r -g scanner -d /app -s /sbin/nologin scanner
RUN chown -R scanner:scanner /app
USER scanner

# 创建数据目录
RUN mkdir -p /app/data/scans /app/data/reports /app/logs \
    && chown -R scanner:scanner /app/data /app/logs

# 环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV PORT=8000

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Optional: Development Image
# ============================================
FROM production AS development

USER root

# 安装开发工具
RUN pip install black flake8 mypy pytest pytest-cov isort

# 切换回开发用户
USER scanner

# 入口点支持热重载
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

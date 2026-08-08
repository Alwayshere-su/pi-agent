# ═══════════════════════════════════════════════════════════════
# Dockerfile — Pi-Agent 文献发现与贝叶斯优化 Agent
# ═══════════════════════════════════════════════════════════════

FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（pdfplumber 等可能需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目源码
COPY . .

# 运行时环境
ENV PYTHONUNBUFFERED=1

# 默认入口
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]

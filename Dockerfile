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

# 安装 Python 依赖（2026-08-16，P2-4 精简）
# 运行时/CI 使用精简集 requirements-test.txt（避开 chromadb/sentence-transformers/
# FlagEmbedding 等 ~3GB 大型 ML 依赖）；完整依赖（requirements.txt）仅用于开发/离线推理，
# 需要时手动 `pip install -r requirements.txt`。
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# 复制项目源码（.dockerignore 已排除 .api_key、备份、临时文件）
COPY . .

# 运行时环境
ENV PYTHONUNBUFFERED=1

# 非 root 运行（P2-4 安全加固）
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 数据卷：workspace 产物/缓存挂载点（P2-4：容器内数据不随镜像固化）
VOLUME ["/app/workspace"]

# 默认入口
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]

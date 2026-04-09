FROM ev-harbor.shell.com.cn/tools/python:3.11-alpine AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY src/ /app/src/

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --upgrade pip && \
    pip wheel --no-cache-dir --prefer-binary -w /wheels .

FROM ev-harbor.shell.com.cn/tools/python:3.11-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OBSERVE_ENABLE_PROMETHEUS="false" \
    PROMETHEUS_URL="" \
    PROMETHEUS_ALIAS_PATH="/app/config/prometheus_aliases.json" \
    SKYWALKING_BASE_URL="" \
    SKYWALKING_TOKEN="" \
    SERVICE_PORT="8000"

WORKDIR /app

COPY --from=builder /wheels /wheels

RUN pip install --no-deps --no-index --find-links=/wheels observe-mcp-server && \
    rm -rf /wheels

# Copy default config files (will be overridden when mounted by k8s)
# COPY config/ /app/config/

EXPOSE 8000

CMD ["observe-mcp-server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000", "--path", "/mcp"]

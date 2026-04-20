# ── Base image ─────────────────────────────────────────────────────────────────
# Python 3.11 slim — minimal image, no unnecessary packages
FROM python:3.11-slim

# ── Metadata ───────────────────────────────────────────────────────────────────
LABEL maintainer="Digamber Dwivedi <digamdip@gmail.com>"
LABEL description="GaadiyaHub Internal Deploy Portal"
LABEL version="1.0.0"

# ── Working directory ──────────────────────────────────────────────────────────
WORKDIR /app

# ── Dependencies ───────────────────────────────────────────────────────────────
# Copy requirements first — Docker caches this layer
# Only reinstalls if requirements.txt changes
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App code ───────────────────────────────────────────────────────────────────
COPY app/ .

# ── Security — run as non-root user ────────────────────────────────────────────
# Never run containers as root — security best practice
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# ── Port ───────────────────────────────────────────────────────────────────────
EXPOSE 5000

# ── Healthcheck ────────────────────────────────────────────────────────────────
# Docker/K8s uses this to know if container is alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# ── Start command ──────────────────────────────────────────────────────────────
# Use gunicorn in production — more robust than Flask dev server
# workers=2 — two parallel request handlers
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
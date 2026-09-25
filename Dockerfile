FROM python:3.11-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.12.6
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend ./backend
COPY migrations ./migrations
COPY alembic.ini ./
RUN groupadd --gid 10001 eicc && useradd --uid 10001 --gid eicc --no-create-home eicc && chown -R eicc:eicc /app
USER eicc
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=45s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["python", "-m", "backend.start"]

FROM backend AS verification
USER root
RUN uv sync --frozen
COPY tests ./tests
COPY scripts ./scripts
RUN chown -R eicc:eicc /app
USER eicc
CMD ["python", "-m", "pytest", "-q", "--junitxml=/tmp/eicc-pytest.xml"]

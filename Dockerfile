FROM python:3.12-slim-bookworm
ENV PATH="/code/.venv/bin:$PATH"
WORKDIR /code


COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/


COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .

# Запускаем через uv, чтобы он видел виртуальное окружение
CMD ["uv", "run", "sh", "-c", "alembic upgrade head && uvicorn app.api.main:app --host 0.0.0.0 --port 8000"]
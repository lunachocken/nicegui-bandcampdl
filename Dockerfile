FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
RUN chmod -R go-w /app
RUN useradd -m appuser
RUN chown -R appuser:appuser /app

HEALTHCHECK CMD python -c "import socket; socket.create_connection(('localhost', 8080), 2)" || exit 1
USER appuser

# Disable development dependencies
ENV UV_NO_DEV=1

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY . /app

# Sync the project into a new environment, asserting the lockfile is up to date

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
# Run the application
CMD ["uv", "run", "main.py"]

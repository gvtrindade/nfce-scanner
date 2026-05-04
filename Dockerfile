FROM python:3.14-slim

# Install system dependencies for Camoufox
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2t64 \
    libgtk-3-0 \
    libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app 

ENV UV_NO_DEV=1

# Set working directory
WORKDIR /app

RUN uv sync --frozen --no-cache

RUN uv run camoufox fetch

# Expose port
EXPOSE 8000

# Command
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
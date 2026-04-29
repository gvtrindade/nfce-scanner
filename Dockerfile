FROM python:3.14-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2t64 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Export lock file to requirements.txt and install
RUN uv export --format requirements-txt > requirements.txt && \
    uv pip install --system -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose port
EXPOSE 8000

# Command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
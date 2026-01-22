# =========================
# Stage 1: Builder
# =========================
FROM python:3.12-slim AS builder

WORKDIR /app

# System deps needed to build wheels
RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Install pip tools
RUN pip install --upgrade pip wheel

# Copy dependency file
COPY requirements.txt .

# Build wheels (cached, faster, cleaner)
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt


# =========================
# Stage 2: Runtime
# =========================
FROM python:3.12-slim

WORKDIR /app

# Install only runtime system deps (usually none, curl optional)
RUN apt-get update && apt-get install -y \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install Python deps from wheels
RUN pip install --no-cache-dir /wheels/*

# Copy application code
COPY . .

# Expose app port (informational)
EXPOSE 8000

# Run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

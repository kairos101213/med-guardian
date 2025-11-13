# Use official Python 3.11 image (forces Python 3.11)
FROM python:3.11.9-slim

# Prevent python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies some packages may need
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY backend/requirements.txt ./requirements.txt

# Upgrade pip and wheel (helps pick binary wheels)
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies (no cache to keep image small)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the repo
COPY . .

# Expose port (Render will provide $PORT)
EXPOSE 8000

# Use the PORT env Render provides; default to 8000 if not set
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

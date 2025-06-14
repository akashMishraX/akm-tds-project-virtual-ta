# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Copy requirement files
COPY requirements.txt /app/

# Install system dependencies & Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy project files into the container
COPY . /app

# Set the entrypoint (adjust main.py if needed)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

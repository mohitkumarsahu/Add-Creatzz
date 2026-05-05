# Use an official Python runtime as a parent image
# 3.10-slim provides a good balance between size and compatibility
FROM python:3.10-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disk
# PYTHONUNBUFFERED: Ensures that python output is sent straight to terminal (useful for logging)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system-level dependencies
# libgl1 and libglib2.0-0 are essential for OpenCV and image processing
# build-essential is included in case any dependencies need to compile C extensions
# nginx is the reverse proxy that routes all services through port 7860
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    procps \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory within the container
WORKDIR /app

# Copy only the requirements file first to take advantage of Docker's layer caching
# This avoids re-installing all dependencies if only the source code changes
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir reduces the image size by not storing the pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory into the container
COPY . .

# Copy nginx config to the standard location
COPY nginx.conf /etc/nginx/nginx.conf

# Make the start script executable
RUN chmod +x start.sh

# HuggingFace Spaces ONLY exposes port 7860 to the internet.
# All internal services (8080, 8100, 8101) are proxied through nginx on 7860.
EXPOSE 7860

# Launch the full application stack via the start script
CMD ["bash", "start.sh"]

# Use an official Python runtime as a parent image
# 3.10-slim provides a good balance between size and compatibility
FROM python:3.10-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to disk
# PYTHONUNBUFFERED: Ensures that python output is sent straight to terminal (useful for logging)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system-level dependencies
# libgl1-mesa-glx and libglib2.0-0 are essential for OpenCV and image processing
# build-essential is included in case any dependencies need to compile C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory within the container
WORKDIR /app

# Copy only the requirements file first to take advantage of Docker's layer caching
# This avoids re-installing all dependencies if only the source code changes
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir reduces the image size by not storing the pip cache
# Note: This project has heavy dependencies (Torch, TensorFlow, PaddlePaddle), so this step will take time.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory into the container
COPY . .

# Expose the ports used by the application components:
# 8080 - Frontend (served via Python's http.server)
# 8100 - Main Backend API (FastAPI - NanaBuild Studio)
# 8101 - Facebook Posting Service (FastAPI)
EXPOSE 8080 8100 8101

# Command to launch the full application stack
# This command starts three concurrent processes:
# 1. A static file server for the frontend (index.html) on port 8080
# 2. The main AI generation backend on port 8100
# 3. The Facebook integration service on port 8101
# 'wait -n' ensures the container exits if any of the core processes fail.
CMD python -m http.server 8080 & \
    python main.py & \
    python facebook_poster/fb_server.py & \
    wait -n

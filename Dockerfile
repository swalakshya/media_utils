# Multi-stage build for Media Utils
# Stage 1: Build React frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm install --legacy-peer-deps

# Copy frontend source
COPY frontend/ ./

# Build frontend for production
RUN npm run build

# Stage 2: Python backend with OCR dependencies
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OCRmyPDF and Tesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OCRmyPDF and Tesseract dependencies
    tesseract-ocr \
    ghostscript \
    img2pdf \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # Tesseract language packs
    tesseract-ocr-hin \
    tesseract-ocr-guj \
    tesseract-ocr-eng \
    tesseract-ocr-mar \
    tesseract-ocr-tam \
    tesseract-ocr-tel \
    # Additional utilities
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./backend/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Create directories for uploads and outputs
RUN mkdir -p /tmp/media_utils_uploads /tmp/media_utils_outputs

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/', timeout=5)"

# Run the FastAPI application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
# Use an official Python slim image for a smaller footprint
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Install system dependencies
# - tesseract-ocr and libtesseract-dev for OCR
# - libgl1 for OpenCV (if needed by other libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure the uploads directory exists
RUN mkdir -p uploads

# Expose the port Render will use
EXPOSE $PORT

# Run the application with Gunicorn
# Using 1 worker and --preload for memory efficiency on Render's 512MB RAM
CMD gunicorn app:app --workers 1 --preload --bind 0.0.0.0:$PORT

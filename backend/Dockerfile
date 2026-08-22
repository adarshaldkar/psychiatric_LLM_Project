# ── MindCare AI Backend — HuggingFace Spaces Dockerfile ──────────────────────
# HF Spaces runs as non-root user and REQUIRES port 7860
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (required by HuggingFace Spaces)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy requirements & install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# HuggingFace Spaces requires port 7860
EXPOSE 7860

# Start production server on port 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

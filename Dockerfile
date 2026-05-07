FROM python:3.12.3-slim

WORKDIR /app

# Install system dependencies needed by the backend
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (for layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the shared package and backend code
COPY shared/ ./shared/
COPY backend/ ./

# Make start.sh executable
RUN chmod +x start.sh

EXPOSE 8000

CMD ["bash", "start.sh"]

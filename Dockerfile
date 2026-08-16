FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    aria2 \
    jq \
    git \
    build-essential \
    libffi-dev \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create downloads folder
RUN mkdir -p /app/DOWNLOADS

# Railway Volumes can be mounted after image build; keep the runtime user
# compatible with the mounted /app/DOWNLOADS directory.

CMD ["python3", "bot.py"]

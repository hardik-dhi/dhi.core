FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/uploads \
    /app/data/audio_uploads \
    /app/frontend/uploads \
    /app/frontend/media \
    /app/frontend/audio \
    /app/logs

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/api/health || exit 1

# Create startup script
RUN echo '#!/bin/bash\n\
echo "🚀 Starting DHI Transaction Analytics System..."\n\
echo "📊 Starting Plaid API Service on port 8080..."\n\
python -m dhi_core.api.app &\n\
sleep 5\n\
echo "🌐 Starting Frontend Dashboard on port 8081..."\n\
python frontend/frontend_server.py &\n\
echo "✅ All services started!"\n\
echo "📱 Dashboard: http://localhost:8081"\n\
echo "🔗 API: http://localhost:8080"\n\
wait' > /app/start.sh && chmod +x /app/start.sh

# Run the application
CMD ["/app/start.sh"]

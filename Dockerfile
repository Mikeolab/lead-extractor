# Lead Extractor Pro - Cloud deployment (Streamlit + FastAPI + Playwright)
# Pin to Bookworm: Playwright install-deps doesn't support Debian Trixie yet
FROM python:3.12-slim-bookworm

# Install system deps for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# Create data dir for SQLite
RUN mkdir -p /app/data /app/exports

EXPOSE 8501
ENV PORT=8501

# Start both servers (FastAPI in background, Streamlit in foreground)
CMD ["/bin/bash", "start_server.sh"]

# Use the latest stable Python image (slim for smaller size)
FROM python:3-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies for security tools
RUN apt-get update && apt-get install -y \
    nmap \
    sqlmap \
    && rm -rf /var/lib/apt/lists/*

# Install Nikto manually since it's not in Debian repos
RUN apt-get update && apt-get install -y git perl && rm -rf /var/lib/apt/lists/* \
    && git clone https://github.com/sullo/nikto.git /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose Flask port
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]

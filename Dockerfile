# SOS Guardian — Production Docker Container
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=5000

# Install system dependencies & requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Create data directory if missing
RUN mkdir -p /app/data

# Expose web service port
EXPOSE 5000

# Start Gunicorn WSGI server
CMD ["gunicorn", "wsgi:app", "--workers", "2", "--bind", "0.0.0.0:5000"]

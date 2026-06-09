FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root runtime user
RUN addgroup --system app \
    && adduser --system --ingroup app --home /app --no-create-home app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Remove any cached Python bytecode that might have been copied
# This ensures fresh .py files are always used
RUN find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
RUN find . -name "*.pyc" -delete 2>/dev/null || true

# Make startup script executable
RUN chmod +x startup.sh \
    && mkdir -p staticfiles media \
    && chown -R app:app staticfiles media

# Expose port
EXPOSE 8000

USER app

# Run startup script
CMD ["./startup.sh", "gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "180", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "--log-level", "info", "tally.wsgi:application"]

FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root

# Copy application code
COPY . /app/ingestion/
ENV PYTHONPATH=/app

# Check GDAL installation
RUN ogr2ogr --version

CMD ["python", "/app/ingestion/run_ingestion.py"]
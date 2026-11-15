FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Set working directory
WORKDIR /app/ingestion

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies, including GeoDataLab-Ingestion
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction

# Copy application code and configuration
COPY . .

# Check GDAL installation
RUN ogr2ogr --version

CMD ["python", "run_ingestion.py"]

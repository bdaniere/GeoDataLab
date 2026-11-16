FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv==0.13.8

# Set working directory
WORKDIR /app/ingestion

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies, including GeoDataLab-Ingestion
RUN uv sync --locked --no-dev

ENV PATH="/app/ingestion/.venv/bin:$PATH"

# Copy application code and configuration
COPY . .

# Check GDAL installation
RUN ogr2ogr --version

CMD ["python", "run_ingestion.py"]

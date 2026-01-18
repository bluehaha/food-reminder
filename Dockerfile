# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only main --no-interaction --no-ansi

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY conf/config.example.yaml ./conf/

# Create state directory
RUN mkdir -p state

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default entrypoint - can be overridden at runtime
ENTRYPOINT ["python"]
CMD ["scripts/check_availability.py", "-c", "conf/config.yaml"]

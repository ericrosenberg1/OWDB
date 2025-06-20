# Use the official Python slim image
FROM python:3.11-slim

# Ensure Python output is unbuffered (useful for Docker logs)
ENV PYTHONUNBUFFERED=1

# Install system dependencies for mysqlclient and pkg-config
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       pkg-config \
       default-libmysqlclient-dev \
       build-essential \
       libssl-dev \
       libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app/OWDB

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose Django’s default port
EXPOSE 8000

# Run the development server (consider replacing with Gunicorn in production)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

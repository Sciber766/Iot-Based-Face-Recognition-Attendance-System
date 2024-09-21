# Use the official Python slim image as a base image
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Expose port 5000 to the outside world
EXPOSE 5000

# Define the command to run your app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

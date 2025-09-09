# Start from an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# We add --no-cache-dir to reduce the image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Command to run the application. We will start with the listener.
# This command will be executed when the container starts.
CMD ["python", "run_listener.py"]
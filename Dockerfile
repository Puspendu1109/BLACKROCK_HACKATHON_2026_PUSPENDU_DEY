# docker build -t blk-hacking-ind-PUSPENDU-DEY .

# Using python:3.11-slim (Debian-based Linux) because it provides a lightweight footprint 
# to keep the image size small, while maintaining excellent compatibility for pre-compiled 
# C-extensions (wheels) often used by libraries like Pydantic and FastAPI.
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Prevent Python from writing pyc files to disc and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5477 as strictly required by the challenge
EXPOSE 5477

# Run the FastAPI application on port 5477
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5477"]
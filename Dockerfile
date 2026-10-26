# Python 3.12-slim — stable, has wheels for all our deps
FROM python:3.12-slim

# Inside the container, create /app folder
WORKDIR /app

# Copy requirements.txt from your computer → container's /app
COPY requirements.txt .

# Inside container, install Python packages from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project from your computer → container's /app
COPY . .

# When container starts, run this command
# uvicorn = web server
# api.main:app = module api/main.py, object app
# --host 0.0.0.0 = listen on all network interfaces
# --port 8000 = on port 8000
# --reload = restart when code changes (for development)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

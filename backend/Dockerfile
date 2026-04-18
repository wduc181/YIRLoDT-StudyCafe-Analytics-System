FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt /tmp/requirements.txt
COPY backend/scoring_engine/requirements.txt /tmp/backend/scoring_engine/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -rf /tmp/requirements.txt /tmp/backend

# Copy backend source code
COPY backend/ /app/

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

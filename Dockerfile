FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pandas scipy python-docx pydantic httpx defusedxml
COPY . .
ENTRYPOINT ["python", "/app/entrypoint.py"]

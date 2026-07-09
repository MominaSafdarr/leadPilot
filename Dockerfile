FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY chroma_data/ ./chroma_data/

EXPOSE 8000

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
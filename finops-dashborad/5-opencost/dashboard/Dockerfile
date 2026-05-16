FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python3 -c "import requests; requests.get('http://localhost:8502/_stcore/health', timeout=5)" \
  || exit 1

CMD ["streamlit", "run", "src/Home.py", \
     "--server.port=8502", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]

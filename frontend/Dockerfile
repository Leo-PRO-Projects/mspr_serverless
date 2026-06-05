# Image du frontend de démonstration (Streamlit) — déployé dans le cluster.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Par défaut en cluster, on appelle la gateway OpenFaaS par son DNS interne.
ENV OPENFAAS_URL=http://gateway.openfaas:8080

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]

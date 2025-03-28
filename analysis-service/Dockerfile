# Dockerfile for analysis-service using python:3.10-slim
FROM python:3.10-slim

# Imposta la cartella di lavoro
WORKDIR /app

# Copia il file dei requirements
COPY requirements.txt .

# Installa netcat-openbsd (fornisce il comando nc) e pulisci la cache di apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Installa le librerie Python necessarie
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto dell'applicazione nella cartella di lavoro
COPY . .

# Rendi eseguibile lo script wait-for-kafka.sh
RUN chmod +x wait-for-kafka.sh

# Avvia lo script di attesa (che poi dovrebbe lanciare l'app)
CMD ["./wait-for-kafka.sh"]

